import { useDebouncedRefHistory } from '@vueuse/core'
import { isEqual } from 'es-toolkit'
import { dayjs } from 'frappe-ui'
import { computed, reactive, ref, toRefs, unref } from 'vue'
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
	MutateArgs,
	Operation,
	OrderByArgs,
	PivotWiderArgs,
	QueryResult,
	QueryResultColumn,
	QueryResultRow,
	Rename,
	SelectArgs,
	SourceArgs,
	SQLArgs,
	Summarize,
	SummarizeArgs,
	UnionArgs,
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
	limit,
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
	let lastExecutionArgs: {
		operations: Operation[]
		adhoc_filters?: AdhocFilters
	}

	async function execute(adhocFilters?: AdhocFilters, force: boolean = false) {
		if (!query.islocal) {
			await waitUntil(() => query.isloaded)
		}

		if (!query.doc.operations.length) {
			result.value = { ...EMPTY_RESULT }
			return
		}

		if (
			!force &&
			lastExecutionArgs &&
			isEqual(lastExecutionArgs, {
				operations: currentOperations.value,
				adhoc_filters: adhocFilters,
			})
		) {
			return Promise.resolve()
		}

		executing.value = true
		return query
			.call('execute', {
				active_operation_idx: activeOperationIdx.value,
				adhoc_filters: adhocFilters,
				force,
			})
			.then((response: any) => {
				if (!response) return

				result.value.executedSQL = response.sql
				result.value.columns = response.columns
				result.value.rows = response.rows
				result.value.totalRowCount = 0
				result.value.formattedRows = getFormattedRows(result.value, query.doc.operations)
				result.value.columnOptions = result.value.columns.map((column) => ({
					label: column.name,
					value: column.name,
					description: column.type,
					query: query.doc.name,
					data_type: column.type,
				}))
				result.value.timeTaken = response.time_taken
				result.value.lastExecutedAt = new Date()
			})
			.catch(() => {
				result.value = { ...EMPTY_RESULT }
			})
			.finally(() => {
				executing.value = false
				lastExecutionArgs = {
					operations: currentOperations.value,
					adhoc_filters: adhocFilters,
				}
			})
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
			})
			.then((count: number) => {
				result.value.totalRowCount = count || 0
			})
			.finally(() => {
				fetchingCount.value = false
			})
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
			title: 'Change Source',
			message: 'Changing the source will clear the current operations. Please confirm.',
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

	function addLimit(args: number) {
		addOperation(limit(args))
	}

	function addPivotWider(args: PivotWiderArgs) {
		addOperation(pivot_wider(args))
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

	function downloadResults() {
		const _downloadResults = () => {
			return query
				.call('download_results', {
					active_operation_idx: activeOperationIdx.value,
				})
				.then((csv_data: string) => {
					if (!csv_data) {
						createToast({
							title: 'Download Failed',
							message: 'No data found to download.',
							variant: 'warning',
						})
						return
					}

					const blob = new Blob([csv_data], { type: 'text/csv' })
					const url = window.URL.createObjectURL(blob)
					const a = document.createElement('a')
					a.setAttribute('hidden', '')
					a.setAttribute('href', url)
					a.setAttribute('download', `${query.doc.title || 'data'}.csv`)
					document.body.appendChild(a)
					a.click()
					document.body.removeChild(a)
				})
		}

		confirmDialog({
			title: 'Download Results',
			message:
				'This action will download the datatable results as a CSV file. Do you want to proceed?',
			primaryActionLabel: 'Yes',
			onSuccess: _downloadResults,
		})
	}

	function getDistinctColumnValues(column: string, search_term: string = '', limit: number = 20) {
		let _activeOperationIdx = activeOperationIdx.value
		if (activeEditIndex.value > -1) {
			_activeOperationIdx = activeEditIndex.value - 1
		}

		return query.call('get_distinct_column_values', {
			active_operation_idx: _activeOperationIdx,
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

	function setSQL(args: SQLArgs) {
		query.doc.operations = []
		if (args.raw_sql.trim().length) {
			query.doc.operations.push(sql(args))
			activeOperationIdx.value = 0
			execute()
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
		return query.save()
			.then(() => {
				createToast({
					title: 'Variables Updated',
					message: 'Script variables have been saved securely.',
					variant: 'success',
				})
			})
			.catch((error) => {
				createToast({
					title: 'Failed to Update Variables',
					message: error.message || 'An error occurred while saving variables.',
					variant: 'error',
				})
				throw error
			})
	}

	function getDrillDownQuery(col: QueryResultColumn, row: QueryResultRow) {
		if (!session.isLoggedIn) {
			return
		}

		const error = validateDrillDown(col, row)
		if (error) {
			createToast({
				title: 'Failed to drill down',
				message: error,
				variant: 'warning',
			})
			return
		}

		const operations = copy(query.doc.operations)
		const reversedOperations = operations.slice().reverse()

		const drill_down_query = useQuery('new-query-' + getUniqueId())
		drill_down_query.doc.title = 'Drill Down'
		drill_down_query.autoExecute = true
		drill_down_query.doc.workbook = query.doc.workbook
		drill_down_query.doc.use_live_connection = query.doc.use_live_connection

		let filters: FilterArgs[] = []
		let sliceIdx = -1
		const rowIndex = result.value.formattedRows.findIndex((r) => r === row)
		const currRow = result.value.rows[rowIndex]

		const lastPivotIdx = reversedOperations.findIndex((op: Operation) => op.type === 'pivot_wider')
		if (lastPivotIdx !== -1) {
			sliceIdx = reversedOperations.length - lastPivotIdx - 1
			filters = getDrillDownQueryForPivot(operations, sliceIdx, col, currRow)
		}

		const lastSummarizeIdx = reversedOperations.findIndex((op: Operation) => op.type === 'summarize')
		if (lastSummarizeIdx !== -1) {
			sliceIdx = reversedOperations.length - lastSummarizeIdx - 1
			filters = getDrillDownQueryForSummarize(operations, sliceIdx, col, currRow)
		}

		drill_down_query.setOperations(operations.slice(0, sliceIdx))
		drill_down_query.addFilterGroup({
			logical_operator: 'And',
			filters: filters,
		})

		return drill_down_query
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
			const start = dayjs(value);

			filters.push({
				column: column(dim.column_name),
				operator: '>=',
				value: start.format('YYYY-MM-DD HH:mm:ss'),
			});

			if (dim.granularity) {
				const end = start.clone().add(1, dim.granularity);
				filters.push({
					column: column(dim.column_name),
					operator: '<',
					value: end.format('YYYY-MM-DD HH:mm:ss'),
				});
			}
		}

		return filters
	}

	function getFiltersForMeasure(measure: Measure, columnName: string) {
		if (measure.measure_name !== columnName || 'expression' in measure === false || !measure.expression) {
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
				return [{
					expression: expression(condition),
				}]
			}
		}

		return []
	}

	function getDrillDownQueryForSummarize(
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

	function getDrillDownQueryForPivot(
		operations: Operation[],
		pivotIdx: number,
		col: QueryResultColumn,
		row: QueryResultRow
	) {
		const drill_down_query = useQuery('new-query-' + getUniqueId())
		drill_down_query.doc.title = 'Drill Down'
		drill_down_query.autoExecute = true
		drill_down_query.doc.workbook = query.doc.workbook
		drill_down_query.doc.use_live_connection = query.doc.use_live_connection
		drill_down_query.setOperations(operations.slice(0, pivotIdx))

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
		const selectedValueColumn = pivotOperation.values.length == 1 ? pivotOperation.values[0].measure_name : pivotColumnValues.at(-1) as string
		pivotOperation.values.forEach((m) => {
			return filters.push(...getFiltersForMeasure(m, selectedValueColumn))
		})

		return filters
	}

	function validateDrillDown(col: QueryResultColumn, row: QueryResultRow) {
		if (!query.doc.operations.find((op) => op.type === 'summarize' || op.type === 'pivot_wider')) {
			return 'Drill down is only supported on summarized data'
		}

		if (!result.value.columns?.length) {
			return 'No columns found in the result'
		}

		if (!row) {
			return 'Row not found'
		}

		if (!result.value.rows?.length) {
			return 'No rows found in the result'
		}

		if (!result.value.formattedRows.find((r) => r === row)) {
			return 'Row not found in the result'
		}
	}

	function copyQuery() {
		query.call('export').then(data => {
			copyToClipboard(JSON.stringify(data, null, 2))
		})
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

	const autoExecute = ref(false)
	watchToggle(currentOperations, () => autoExecute.value && execute(), {
		immediate: true,
		deep: true,
		toggleCondition: () => autoExecute.value,
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

		autoExecute,
		executing,
		fetchingCount,
		result,

		execute,
		fetchResultCount,

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
		addLimit,
		addPivotWider,
		selectColumns,
		renameColumn,
		removeColumn,
		changeColumnType,
		addCustomOperation,

		getDistinctColumnValues,
		getColumnsForSelection,
		downloadResults,

		getSQLOperation,
		setSQL,

		getCodeOperation,
		setCode,
		updateVariables,

		dimensions,
		measures,
		getDimension,
		getMeasure,

		getDrillDownQuery,
		copy: copyQuery,

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
