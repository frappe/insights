import { useDebouncedRefHistory } from '@vueuse/core'
import { Buffer } from 'buffer'
import { isEqual } from 'es-toolkit'
import { call, dayjs } from 'frappe-ui'
import { computed, reactive, ref, toRefs, unref, watch } from 'vue'
import {
	copy,
	copyToClipboard,
	getUniqueId,
	safeJSONParse,
	waitUntil,
	watchToggle,
	wheneverChanges,
} from '../helpers'
import { confirmDialog } from '../helpers/confirm_dialog'
import { FIELDTYPES } from '../helpers/constants'
import useDocumentResource from '../helpers/resource'
import { createToast } from '../helpers/toasts'
import { __ } from '../translation'
import router from '../router'
import session from '../session'
import {
	AdhocFilters,
	CodeArgs,
	ColumnDataType,
	ColumnOption,
	CustomOperationArgs,
	Dimension,
	FilterArgs,
	FilterGroupArgs,
	FilterRule,
	JoinArgs,
	Measure,
	Mutate,
	MutateArgs,
	Operation,
	OrderByArgs,
	PivotWiderArgs,
	QueryResult,
	QueryResultColumn,
	QueryResultRow,
	Rename,
	SelectArgs,
	Source,
	SourceArgs,
	SQLArgs,
	Summarize,
	SummarizeArgs,
	UnionArgs,
	aggregations,
} from '../types/query.types'
import { InsightsQueryv3, QueryVariable } from '../types/workbook.types'
import useWorkbook from '../workbook/workbook'
import {
	cast,
	code,
	column,
	custom_operation,
	expression,
	filter_group,
	getDimensions,
	getFormattedRows,
	getMeasures,
	join,
	mutate,
	order_by,
	pivot_wider,
	remove,
	rename,
	select,
	source,
	sql,
	summarize,
	union,
} from './helpers'

const queries = new Map<string, Query>()

export default function useQuery(name: string) {
	const key = String(name)
	const existingQuery = queries.get(key)
	if (existingQuery) return existingQuery

	const query = makeQuery(name)
	queries.set(key, query)
	return query
}

export function makeQuery(name: string) {
	const query = getQueryResource(name)

	const activeOperationIdx = ref(-1)
	query.onAfterLoad(() => {
		activeOperationIdx.value = query.doc.operations.length - 1
	})

	const currentOperations = computed(() => {
		if (activeOperationIdx.value >= 0) {
			return query.doc.operations.slice(0, activeOperationIdx.value + 1)
		}
		return query.doc.operations.slice()
	})

	const measureColumns = computed(() => {
		const measureNames = new Set<string>()
		let seenSummarize = false
		for (const op of currentOperations.value) {
			if (op.type === 'summarize') {
				op.measures.forEach((m) => measureNames.add(m.measure_name))
				seenSummarize = true
			} else if (op.type === 'pivot_wider') {
				op.values.forEach((m) => measureNames.add(m.measure_name))
				seenSummarize = true
			} else if (seenSummarize && op.type === 'rename') {
				// Track renames that happen after a summarize/pivot_wider so that
				// a measure renamed to e.g. "total_revenue" is still detected.
				if (measureNames.has(op.column.column_name)) {
					measureNames.delete(op.column.column_name)
					measureNames.add(op.new_name)
				}
			}
		}
		return Array.from(measureNames)
	})

	const dataSource = computed(() => getDataSource(currentOperations.value))

	function getDataSource(operations: Operation[]): string {
		const sourceOp = operations.find((op) => op.type === 'source')
		if (!sourceOp) return ''
		if (sourceOp.table.type === 'table') {
			return sourceOp.table.data_source
		}
		if (sourceOp.table.type === 'query' && 'query_name' in sourceOp.table) {
			const sourceQuery = useQuery(sourceOp.table.query_name)
			return getDataSource(sourceQuery.currentOperations)
		}
		return ''
	}

	const activeEditIndex = ref(-1)
	const activeEditOperation = computed<Operation>(() => {
		if (activeEditIndex.value === -1) return {} as Operation
		return query.doc.operations[activeEditIndex.value]
	})

	const result = ref({ ...EMPTY_RESULT })
	const executing = ref(false)
	const downloading = ref(false)
	const currentDownloadToken = ref<number | null>(null)
	const currentPage = ref(1)
	const pageSize = ref(100)
	let lastExecutionArgs: {
		operations: Operation[]
		adhoc_filters?: AdhocFilters
		page?: number
		page_size?: number
	}
	let currentExecutionToken = 0

	const adhocFilters = ref<AdhocFilters>()
	async function execute(force: boolean = false, page_size?: number) {
		if (!query.islocal) {
			await waitUntil(() => query.isloaded)
		}

		if (!query.doc.operations.length) {
			result.value = { ...EMPTY_RESULT }
			return
		}

		if (page_size) {
			pageSize.value = page_size
			currentPage.value = 1
		}

		if (
			!force &&
			lastExecutionArgs &&
			isEqual(lastExecutionArgs, {
				operations: currentOperations.value,
				adhoc_filters: adhocFilters.value,
				page: currentPage.value,
				page_size: pageSize.value,
			})
		) {
			return Promise.resolve()
		}

		executing.value = true
		const token = ++currentExecutionToken
		return query
			.call('execute', {
				active_operation_idx: activeOperationIdx.value,
				adhoc_filters: adhocFilters.value,
				force,
				page: currentPage.value,
				page_size: pageSize.value,
			})
		.then((response: any) => {
			// Discard stale responses — a newer execution has superseded this one
			if (token !== currentExecutionToken) return
			if (!response) return

			result.value.executedSQL = response.sql
			result.value.columns = response.columns
			result.value.rows = response.rows
			result.value.totalRowCount = 0
			result.value.formattedRows = getFormattedRows(result.value, query.doc.operations)

			const aggregationPrefixes = aggregations.map((a) => `${a}_`)
			const isMeasureColumn = (name: string) =>
				measureColumns.value.includes(name) ||
				aggregationPrefixes.some((prefix) => name.startsWith(prefix))

			result.value.columnOptions = result.value.columns.map((column) => {
				return {
					label: column.name,
					value: column.name,
					description: column.type,
					query: query.doc.name,
					data_type: column.type,
					is_measure: isMeasureColumn(column.name),
				}
			})
			result.value.timeTaken = response.time_taken
			result.value.lastExecutedAt = new Date()
		})
			.catch(() => {
				if (token !== currentExecutionToken) return
				result.value = { ...EMPTY_RESULT }
			})
			.finally(() => {
				if (token !== currentExecutionToken) return
				executing.value = false
				lastExecutionArgs = {
					operations: currentOperations.value,
					adhoc_filters: adhocFilters.value,
					page: currentPage.value,
					page_size: pageSize.value,
				}
			})
	}

	function goToPage(page: number) {
		if (page < 1) return
		currentPage.value = page
		execute()
	}

	const fetchingCount = ref(false)
	async function fetchResultCount() {
		if (!query.islocal) {
			await waitUntil(() => query.isloaded)
		}

		if (!query.doc.operations.length) {
			result.value.totalRowCount = 0
			return
		}

		fetchingCount.value = true
		return query
			.call('get_count', {
				active_operation_idx: activeOperationIdx.value,
				adhoc_filters: adhocFilters.value,
			})
			.then((count: number) => {
				result.value.totalRowCount = count || 0
			})
			.finally(() => {
				fetchingCount.value = false
			})
	}

	async function formatSQL(args: SQLArgs): Promise<string> {
		if (!args.raw_sql.trim()) return args.raw_sql || ''

		try {
			const formattedSQL = await query.call('format', { raw_sql: args.raw_sql.trim() })
			const sqlOp = getSQLOperation()
			if (sqlOp) {
				sqlOp.raw_sql = formattedSQL
			} else {
				console.warn('No SQL operation found for native query.')
			}
			return formattedSQL
		} catch (error) {
			console.error('Error formatting SQL:', error)
			return args.raw_sql
		}
	}

	function setActiveOperation(index: number) {
		activeOperationIdx.value = index
		activeEditIndex.value = -1
	}

	function setActiveEditIndex(index: number) {
		activeEditIndex.value = index
	}

	function removeOperation(index: number) {
		query.doc.operations.splice(index, 1)
		if (index > activeOperationIdx.value) return
		activeOperationIdx.value--
		activeOperationIdx.value = Math.max(activeOperationIdx.value, -1)
	}

	function setSource(args: SourceArgs) {
		const editingSource = activeEditOperation.value.type === 'source'

		const _setSource = () => {
			if (editingSource) {
				query.doc.operations[activeEditIndex.value] = source(args)
				setActiveEditIndex(-1)
			} else {
				query.doc.operations = [source(args)]
				activeOperationIdx.value = 0
			}

			if (query.doc.title?.match(/Query \d+/) && 'table_name' in args.table) {
				query.doc.title = args.table.table_name
			}

			if (args.table.type == 'query') {
				const sourceQuery = useQuery(args.table.query_name)
				query.doc.use_live_connection = unref(sourceQuery.doc.use_live_connection)
			}
		}
		if (!query.doc.operations.length || editingSource) {
			_setSource()
			return
		}
		confirmDialog({
			title: __('Change Source'),
			message: __('Changing the source will clear the current operations. Please confirm.'),
			onSuccess: _setSource,
		})
	}

	function addOperation(op: Operation) {
		query.doc.operations.splice(activeOperationIdx.value + 1, 0, op)
		activeOperationIdx.value++
	}

	function addJoin(args: JoinArgs) {
		const editingJoin = activeEditOperation.value.type === 'join'

		if (!editingJoin) {
			addOperation(join(args))
		} else {
			query.doc.operations[activeEditIndex.value] = join(args)
			setActiveEditIndex(-1)
		}
	}

	function addUnion(args: UnionArgs) {
		const editingUnion = activeEditOperation.value.type === 'union'

		if (!editingUnion) {
			addOperation(union(args))
		} else {
			query.doc.operations[activeEditIndex.value] = union(args)
			setActiveEditIndex(-1)
		}
	}

	function addFilterGroup(args: FilterGroupArgs) {
		const editingFilter =
			activeEditOperation.value.type === 'filter_group' ||
			activeEditOperation.value.type === 'filter'

		if (!editingFilter) {
			addOperation(filter_group(args))
		} else {
			query.doc.operations[activeEditIndex.value] = filter_group(args)
			setActiveEditIndex(-1)
		}
	}

	function addMutate(args: MutateArgs) {
		const editingMutate = activeEditOperation.value.type === 'mutate'

		if (!editingMutate) {
			addOperation(mutate(args))
		} else {
			query.doc.operations[activeEditIndex.value] = mutate(args)
			setActiveEditIndex(-1)
		}
	}

	function addSummarize(args: SummarizeArgs) {
		const editingSummarize = activeEditOperation.value.type === 'summarize'

		if (!editingSummarize) {
			addOperation(summarize(args))
		} else {
			query.doc.operations[activeEditIndex.value] = summarize(args)
			setActiveEditIndex(-1)
		}
	}

	function addOrderBy(args: OrderByArgs) {
		const existingOrderBy = currentOperations.value.find(
			(op) =>
				op.type === 'order_by' &&
				op.column.column_name === args.column.column_name &&
				op.direction === args.direction
		)
		if (existingOrderBy) return

		const existingOrderByIndex = currentOperations.value.findIndex(
			(op) => op.type === 'order_by' && op.column.column_name === args.column.column_name
		)
		if (existingOrderByIndex > -1) {
			query.doc.operations[existingOrderByIndex] = order_by(args)
		} else {
			addOperation(order_by(args))
		}
	}

	function removeOrderBy(column_name: string) {
		const index = query.doc.operations.findIndex(
			(op) => op.type === 'order_by' && op.column.column_name === column_name
		)
		if (index > -1) {
			query.doc.operations.splice(index, 1)
		}
	}

	function addPivotWider(args: PivotWiderArgs) {
		const editingPivot = activeEditOperation.value.type === 'pivot_wider'

		if (!editingPivot) {
			addOperation(pivot_wider(args))
		} else {
			query.doc.operations[activeEditIndex.value] = pivot_wider(args)
			setActiveEditIndex(-1)
		}
	}

	function selectColumns(args: SelectArgs) {
		const editingSelect = activeEditOperation.value.type === 'select'

		if (!editingSelect) {
			addOperation(select(args))
		} else {
			query.doc.operations[activeEditIndex.value] = select(args)
			setActiveEditIndex(-1)
		}
	}

	function renameColumn(oldName: string, newName: string) {
		// Check if there's a mutate operation with the old name
		const existingMutateIdx = currentOperations.value.findIndex(
			(op) => op.type === 'mutate' && op.new_name === oldName
		)

		if (existingMutateIdx !== -1) {
			// Update the new_name property of the existing mutate operation
			const mutateOp = query.doc.operations[existingMutateIdx] as Mutate
			query.doc.operations[existingMutateIdx] = {
				...mutateOp,
				new_name: newName,
			}
			return
		}

		const existingRenameIdx = currentOperations.value.findIndex(
			(op) => op.type === 'rename' && op.new_name === oldName
		)

		if (existingRenameIdx === -1) {
			// No existing rename, add new one
			addOperation(
				rename({
					column: column(oldName),
					new_name: newName,
				})
			)
			return
		}

		const existingRename = currentOperations.value[existingRenameIdx] as Rename
		const originalColumnName = existingRename.column.column_name

		// If renaming back to original name, remove the rename operation
		if (originalColumnName === newName) {
			removeOperation(existingRenameIdx)
			return
		}

		// Update existing rename operation
		query.doc.operations.splice(existingRenameIdx, 1)
		addOperation(
			rename({
				column: column(originalColumnName),
				new_name: newName,
			})
		)
	}

	function removeColumn(column_names: string | string[]) {
		if (!Array.isArray(column_names)) {
			column_names = [column_names]
		}

		// if last operation is remove operation, append to it
		const lastOperation = query.doc.operations[activeOperationIdx.value]
		if (lastOperation?.type === 'remove') {
			query.doc.operations[activeOperationIdx.value] = remove({
				column_names: [...lastOperation.column_names, ...column_names],
			})
		} else {
			addOperation(remove({ column_names }))
		}
	}

	function changeColumnType(column_name: string, newType: ColumnDataType) {
		// Check if there's a mutate operation with the old name
		const existingMutateIdx = currentOperations.value.findIndex(
			(op) => op.type === 'mutate' && op.new_name === column_name
		)

		if (existingMutateIdx !== -1) {
			// Update the new_name property of the existing mutate operation
			const mutateOp = query.doc.operations[existingMutateIdx] as Mutate
			query.doc.operations[existingMutateIdx] = {
				...mutateOp,
				data_type: newType,
			}
			return
		}

		addOperation(
			cast({
				column: column(column_name),
				data_type: newType,
			})
		)
	}

	function addCustomOperation(args: CustomOperationArgs) {
		const editingCustomOperation = activeEditOperation.value.type === 'custom_operation'

		if (!editingCustomOperation) {
			addOperation(custom_operation(args))
		} else {
			query.doc.operations[activeEditIndex.value] = custom_operation(args)
			setActiveEditIndex(-1)
		}
	}

	function setOperations(newOperations: Operation[]) {
		query.doc.operations = newOperations
		activeOperationIdx.value = newOperations.length - 1
	}

	function downloadResults(format: string = 'csv', filename?: string) {
		const _downloadResults = () => {
			downloading.value = true
			const token = Date.now() + Math.random()
			currentDownloadToken.value = token
			return call('insights.api.run_doc_method', {
				method: 'download_results',
				docs: {
					...(query.doc || {}),
					__islocal: query.islocal,
				},
				args: {
					format,
					active_operation_idx: activeOperationIdx.value,
					adhoc_filters: adhocFilters.value,
				},
			})
				.then((payload: any) => {
					if (currentDownloadToken.value !== token) return
					const data: string = payload?.message
					if (!data) {
						createToast({
							title: __('Download Failed'),
							message: __('No data found to download.'),
							variant: 'warning',
						})
						return
					}

					let blob: Blob
					let extension: string
					let mimeType: string

					if (format === 'excel') {
						const bytes = Buffer.from(data, 'base64')
						blob = new Blob([bytes], {
							type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
						})
						extension = 'xlsx'
						mimeType = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
					} else {
						blob = new Blob([data], { type: 'text/csv' })
						extension = 'csv'
						mimeType = 'text/csv'
					}

					const url = window.URL.createObjectURL(blob)
					const a = document.createElement('a')
					a.setAttribute('hidden', '')
					a.setAttribute('href', url)
					const finalFileName = `${filename || query.doc.title || 'data'}.${extension}`
					a.setAttribute('download', finalFileName)
					document.body.appendChild(a)
					a.click()
					document.body.removeChild(a)
					window.URL.revokeObjectURL(url)
					createToast({
						title: __('Export Successful'),
						message: __(`File "{0}" exported successfully`, finalFileName),
						variant: 'success',
					})
				})
				.catch((error: any) => {
					if (currentDownloadToken.value !== token) return
					createToast({
						title: __('Download Failed'),
						message: error?.message || __('Failed to download file'),
						variant: 'error',
					})
				})
				.finally(() => {
					if (currentDownloadToken.value === token) {
						downloading.value = false
						currentDownloadToken.value = null
					}
				})
		}

		_downloadResults()
	}

	function cancelDownload() {
		currentDownloadToken.value = null
		downloading.value = false
	}

	function exportResults(format: string, filename: string) {
		downloadResults(format, filename)
	}

	function getDistinctColumnValues(column: string, search_term: string = '', limit: number = 20) {
		let _activeOperationIdx = activeOperationIdx.value
		if (activeEditIndex.value > -1) {
			_activeOperationIdx = activeEditIndex.value - 1
		}

		return query.call('get_distinct_column_values', {
			active_operation_idx: _activeOperationIdx,
			adhoc_filters: adhocFilters.value,
			column_name: column,
			search_term,
			limit,
		})
	}

	function getColumnsForSelection(): Promise<ColumnOption[]> {
		let _activeOperationIdx = activeOperationIdx.value
		if (activeEditIndex.value > -1) {
			_activeOperationIdx = activeEditIndex.value - 1
		}

		return query
			.call('get_columns_for_selection', {
				active_operation_idx: _activeOperationIdx,
			})
			.then((columns: QueryResultColumn[]) => {
				return columns.map((column) => ({
					label: column.name,
					value: column.name,
					description: column.type,
					query: query.doc.name,
					data_type: column.type,
				}))
			})
	}

	const dimensions = computed(() => getDimensions(result.value.columns))
	const measures = computed(() => getMeasures(result.value.columns))

	function getDimension(column_name: string) {
		return dimensions.value.find((d) => d.column_name === column_name)
	}
	function getMeasure(column_name: string) {
		return measures.value.find((m) => m.measure_name === column_name)
	}

	function getSQLOperation() {
		if (!query.doc.is_native_query) return ''
		return query.doc.operations.find((op) => op.type === 'sql')
	}

	function setSQL(args: SQLArgs, force: boolean = false) {
		query.doc.operations = []
		if (args.raw_sql.trim().length) {
			query.doc.operations.push(sql(args))
			activeOperationIdx.value = 0
			execute(force)
		} else {
			activeOperationIdx.value = -1
		}
	}

	function getCodeOperation() {
		return query.doc.operations.find((op) => op.type === 'code')
	}

	function setCode(args: CodeArgs) {
		query.doc.operations = []
		if (args.code.trim().length) {
			query.doc.operations.push(code(args))
			activeOperationIdx.value = 0
		} else {
			activeOperationIdx.value = -1
		}
	}

	function updateVariables(variables: QueryVariable[]) {
		if (!query.doc.is_script_query) return Promise.resolve()

		query.doc.variables = variables
		return query
			.save()
			.then(() => {
				createToast({
					title: __('Variables Updated'),
					message: __('Script variables have been saved securely.'),
					variant: 'success',
				})
			})
			.catch((error) => {
				createToast({
					title: __('Failed to Update Variables'),
					message: error.message || __('An error occurred while saving variables.'),
					variant: 'error',
				})
				throw error
			})
	}

	async function getDrillDownQuery(col: QueryResultColumn, row: QueryResultRow) {
		if (!session.isLoggedIn) {
			return
		}

		const rowIndex = result.value.formattedRows.findIndex((r) => r === row)
		const currRow = result.value.rows[rowIndex]

		// Get the effective operations — inlining source query ops if needed
		const operations = await getEffectiveOperationsForDrillDown(
			copy(query.doc.operations),
			currRow,
			col,
		)
		if (!operations) {
			// error toast was already shown
			return
		}

		const { ops, filters: inheritedFilters } = operations

		// Now find the last summarize/pivot in the resolved operations
		const reversedOps = ops.slice().reverse()

		let drillDownFilters: FilterArgs[] = []
		let sliceIdx = -1

		const lastPivotIdx = reversedOps.findIndex((op: Operation) => op.type === 'pivot_wider')
		if (lastPivotIdx !== -1) {
			sliceIdx = reversedOps.length - lastPivotIdx - 1
			drillDownFilters = getDrillDownFiltersForPivot(ops, sliceIdx, col, currRow)
		}

		const lastSummarizeIdx = reversedOps.findIndex((op: Operation) => op.type === 'summarize')
		if (lastSummarizeIdx !== -1) {
			sliceIdx = reversedOps.length - lastSummarizeIdx - 1
			drillDownFilters = getDrillDownFiltersForSummarize(ops, sliceIdx, col, currRow)
		}

		const drill_down_query = useQuery('new-query-' + getUniqueId())
		drill_down_query.doc.title = 'Drill Down'
		drill_down_query.doc.use_live_connection = query.doc.use_live_connection
		drill_down_query.autoExecute = true

		drill_down_query.setOperations(ops.slice(0, sliceIdx))
		drill_down_query.addFilterGroup({
			logical_operator: 'And',
			filters: [...inheritedFilters, ...drillDownFilters],
		})

		return drill_down_query
	}

	/**
	 * Returns the effective operations list for drill-down.
	 *
	 * If the current operations already have a summarize/pivot, return them as-is.
	 * Otherwise, if the source is another query, inline that source query's operations
	 * (prepending any filters from the current query) so the drill-down can find the
	 * source query's summarize and slice through it.
	 *
	 * Returns null and shows a toast if drill-down is not possible.
	 */
	async function getEffectiveOperationsForDrillDown(
		operations: Operation[],
		currRow: QueryResultRow,
		col: QueryResultColumn,
		_visitedQueryNames: string[] = [],
	): Promise<{ ops: Operation[]; filters: FilterArgs[] } | null> {
		// If there's a local summarize/pivot, no inlining needed
		const hasSummarizeOrPivot = operations.find(
			(op) => op.type === 'summarize' || op.type === 'pivot_wider',
		)
		if (hasSummarizeOrPivot) {
			// Basic validation
			if (!result.value.columns?.length) {
				createToast({
					title: __('Failed to drill down'),
					message: 'No columns found in the result',
					variant: 'warning',
				})
				return null
			}
			if (!currRow) {
				createToast({
					title: __('Failed to drill down'),
					message: 'Row not found',
					variant: 'warning',
				})
				return null
			}
			return { ops: operations, filters: [] }
		}

		// No local summarize/pivot — check if the source is another query
		const sourceOp = operations.find((op) => op.type === 'source') as Source | undefined
		if (
			!sourceOp ||
			sourceOp.table.type !== 'query'
		) {
			createToast({
				title: __('Failed to drill down'),
				message: __('Drill down is only supported on summarized data'),
				variant: 'warning',
			})
			return null
		}

		const sourceQueryName = sourceOp.table.query_name

		// Guard against circular references
		if (_visitedQueryNames.includes(sourceQueryName)) {
			createToast({
				title: __('Failed to drill down'),
				message: __('Drill down is only supported on summarized data'),
				variant: 'warning',
			})
			return null
		}

		// Load the source query's operations
		const sourceQuery = useQuery(sourceQueryName)
		await waitUntil(() => sourceQuery.isloaded)

		const sourceOps = copy(sourceQuery.doc.operations)

		// Merge: source query's operations + any filter_groups from the current query
		// (filters applied on top of the source query should still be respected)
		const mergedOps = [
			...sourceOps,
			...operations.filter((op) => op.type === 'filter_group'),
		]

		// Recursively resolve — the source query might itself have a query source
		return getEffectiveOperationsForDrillDown(
			mergedOps,
			currRow,
			col,
			[..._visitedQueryNames, sourceQueryName],
		)
	}

	function getFiltersForDimension(dim: Dimension, value: string) {
		const filters: FilterRule[] = []

		if (!FIELDTYPES.DATE.includes(dim.data_type)) {
			filters.push({
				column: column(dim.column_name),
				operator: '=',
				value: value,
			})
		}

		if (FIELDTYPES.DATE.includes(dim.data_type)) {
			if (!value) {
				filters.push({ column: column(dim.column_name), operator: 'is_not_set', value: '' })
				return filters
			}

			const start = dayjs(value)
			// since fiscal year is not supported in dayjs
			// we will treat it as year for drill down purposes
			const granularity = dim.granularity === 'fiscal_year' ? 'year' : dim.granularity

			filters.push({
				column: column(dim.column_name),
				operator: '>=',
				value: start.format('YYYY-MM-DD HH:mm:ss'),
			})

			if (granularity) {
				const end = start.clone().add(1, granularity)
				filters.push({
					column: column(dim.column_name),
					operator: '<',
					value: end.format('YYYY-MM-DD HH:mm:ss'),
				})
			}
		}

		return filters
	}

	function getFiltersForMeasure(measure: Measure, columnName: string) {
		if (
			measure.measure_name !== columnName ||
			'expression' in measure === false ||
			!measure.expression
		) {
			return []
		}

		// patterns to match to extract the condition
		// 1. count_if(order_status == 'delivered')
		// 2. count_if(order_status == 'delivered', order_id)
		// 3. sum_if(order_status == 'delivered', order_id)
		// 4. distinct_count_if(order_status == 'delivered', order_id)
		const exp = measure.expression.expression
		const patterns = [
			/^count_if\(([^,]+),\s*([^)]+)\)$/,
			/^count_if\(([^,]+)\)$/,
			/^sum_if\(([^,]+),\s*([^)]+)\)$/,
			/^distinct_count_if\(([^,]+),\s*([^)]+)\)$/,
		]
		const pattern = patterns.find((p) => exp.match(p))
		if (pattern) {
			const match = exp.match(pattern)
			if (match) {
				const condition = match[1].trim()
				return [
					{
						expression: expression(condition),
					},
				]
			}
		}

		return []
	}

	function getDrillDownFiltersForSummarize(
		operations: Operation[],
		summarizeIdx: number,
		col: QueryResultColumn,
		row: QueryResultRow
	) {
		const filters: FilterArgs[] = []
		const summarizeOperation = operations[summarizeIdx] as Summarize
		summarizeOperation.dimensions.forEach((c) => {
			filters.push(...getFiltersForDimension(c, row[c.dimension_name]))
		})

		summarizeOperation.measures.forEach((m) => {
			filters.push(...getFiltersForMeasure(m, col.name))
		})

		return filters
	}

	function getDrillDownFiltersForPivot(
		operations: Operation[],
		pivotIdx: number,
		col: QueryResultColumn,
		row: QueryResultRow
	) {
		const pivotOperation = operations[pivotIdx] as PivotWiderArgs

		const filters: FilterArgs[] = []
		pivotOperation.rows.forEach((c) => {
			filters.push(...getFiltersForDimension(c, row[c.dimension_name]))
		})

		const pivotColumnValues = col.name.split('___').reverse()
		// each value in the pivot column values corresponds to a column in the pivot operation "columns"
		// for eg. if the pivot column values are ["A", "B", "C"], then these values correspond to
		// pivotOperation.columns[0], pivotOperation.columns[1], pivotOperation.columns[2]
		pivotOperation.columns.forEach((c, idx) => {
			if (pivotColumnValues[idx]) {
				filters.push(...getFiltersForDimension(c, pivotColumnValues[idx]))
			}
		})

		// if there are more than one value then there are two headers in the pivot table
		// the last one displays the measure name, so we get the current measure name from pivotColumnValues
		const selectedValueColumn =
			pivotOperation.values.length == 1
				? pivotOperation.values[0].measure_name
				: (pivotColumnValues[pivotColumnValues.length - 1] as string)
		pivotOperation.values.forEach((m) => {
			return filters.push(...getFiltersForMeasure(m, selectedValueColumn))
		})

		return filters
	}


	function copyQuery() {
		query.call('export').then((data) => {
			copyToClipboard(JSON.stringify(data, null, 2))
		})
	}

	function duplicateQuery() {
		const workbook = useWorkbook(query.doc.workbook)
		return query
			.call('duplicate')
			.then((newQueryName: string) => {
				createToast({
					title: __('Query duplicated'),
					variant: 'success',
				})
				router.push(`/workbook/${query.doc.workbook}/query/${newQueryName}`)
			})
			.then(workbook.load)
	}

	const history = useDebouncedRefHistory(
		// @ts-ignore
		computed({
			get() {
				return {
					doc: query.doc,
					activeOperationIdx: activeOperationIdx.value,
					activeEditIndex: activeEditIndex.value,
				}
			},
			set(value) {
				Object.assign(query.doc, value.doc)
				activeOperationIdx.value = value.activeOperationIdx
				activeEditIndex.value = value.activeEditIndex
			},
		}),
		{
			deep: true,
			capacity: 100,
			debounce: 500,
		}
	)

	const importingTables = ref(false)
	async function refreshStoredTables() {
		importingTables.value = true
		try {
			const response = await query.call('refresh_stored_tables')
			createToast({
				title: __('Import Started'),
				message: response?.message || __('Importing tables to data store'),
				variant: 'success',
			})
		} catch (error: any) {
			createToast({
				title: __('Import Failed'),
				message: error?.message || __('Failed to import tables to data store'),
				variant: 'error',
			})
		} finally {
			importingTables.value = false
		}
	}

	const autoExecute = ref(false)
	watchToggle(currentOperations, () => autoExecute.value && execute(), {
		immediate: true,
		deep: true,
		toggleCondition: () => autoExecute.value,
	})

	watch(currentOperations, () => {
		currentPage.value = 1
		result.value.totalRowCount = 0
	})

	waitUntil(() => query.isloaded).then(() => {
		wheneverChanges(
			() => query.doc.title,
			() => {
				if (!query.doc.workbook) return
				const workbook = useWorkbook(query.doc.workbook)
				for (const q of workbook.doc.queries) {
					if (q.name === query.doc.name) {
						q.title = query.doc.title
						break
					}
				}
			},
			{ debounce: 500 }
		)
	})

	return reactive({
		...toRefs(query),

		activeOperationIdx,
		activeEditIndex,
		dataSource,
		currentOperations,
		activeEditOperation,
		adhocFilters,

		autoExecute,
		executing,
		fetchingCount,
		result,

		currentPage,
		pageSize,
		goToPage,

		execute,
		fetchResultCount,
		refreshStoredTables,
		importingTables,

		setOperations,
		setActiveOperation,
		setActiveEditIndex,
		removeOperation,
		setSource,
		addJoin,
		addUnion,
		addFilterGroup,
		addMutate,
		addSummarize,
		addOrderBy,
		removeOrderBy,
		addPivotWider,
		selectColumns,
		renameColumn,
		removeColumn,
		changeColumnType,
		addCustomOperation,

		getDistinctColumnValues,
		getColumnsForSelection,
		downloadResults,
		exportResults,
		downloading,
		cancelDownload,
		getSQLOperation,
		setSQL,
		formatSQL,

		getCodeOperation,
		setCode,
		updateVariables,

		dimensions,
		measures,
		getDimension,
		getMeasure,

		getDrillDownQuery,
		copy: copyQuery,
		duplicate: duplicateQuery,

		history,
		canUndo() {
			return !activeEditIndex.value && !executing.value
		},
		canRedo() {
			return !activeEditIndex.value && !executing.value
		},
	})
}

export const EMPTY_RESULT: QueryResult = {
	executedSQL: '',
	totalRowCount: 0,
	rows: [],
	formattedRows: [],
	columns: [],
	columnOptions: [],
	timeTaken: 0,
	lastExecutedAt: new Date(),
}

export type Query = ReturnType<typeof makeQuery>

const INITIAL_DOC: InsightsQueryv3 = {
	doctype: 'Insights Query v3',
	name: '',
	owner: '',
	title: '',
	workbook: '',
	operations: [],
	read_only: false,
	sort_order: 0,
}

function getQueryResource(name: string) {
	const doctype = 'Insights Query v3'
	const query = useDocumentResource<InsightsQueryv3>(doctype, name, {
		initialDoc: { ...INITIAL_DOC, name },
		enableAutoSave: true,
		disableLocalStorage: true,
		transform: transformQueryDoc,
	})
	wheneverChanges(
		() => query.doc.read_only,
		() => {
			if (query.doc.read_only) {
				query.autoSave = false
			}
		}
	)
	return query
}

function transformQueryDoc(doc: any) {
	doc.operations = safeJSONParse(doc.operations) || []
	if (
		doc.is_native_query === undefined &&
		doc.is_script_query === undefined &&
		doc.is_builder_query === undefined
	) {
		doc.is_builder_query = true
	}
	return doc
}

export function newQuery() {
	return getQueryResource('new-query-' + getUniqueId())
}
