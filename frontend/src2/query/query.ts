import { useDebouncedRefHistory } from '@vueuse/core'
import { computed, reactive, ref, toRefs, unref } from 'vue'
import { getUniqueId, safeJSONParse, showErrorToast, waitUntil, wheneverChanges } from '../helpers'
import { confirmDialog } from '../helpers/confirm_dialog'
import useDocumentResource from '../helpers/resource'
import {
	AdhocFilters,
	CodeArgs,
	ColumnDataType,
	ColumnOption,
	CustomOperationArgs,
	FilterGroupArgs,
	JoinArgs,
	MutateArgs,
	Operation,
	OrderByArgs,
	PivotWiderArgs,
	QueryResult,
	QueryResultColumn,
	Rename,
	SelectArgs,
	SourceArgs,
	SQLArgs,
	SummarizeArgs,
	UnionArgs,
} from '../types/query.types'
import { InsightsQueryv3 } from '../types/workbook.types'
import useWorkbook from '../workbook/workbook'
import {
	cast,
	code,
	column,
	custom_operation,
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
	let lastExecutionId = ''
	async function execute(adhocFilters?: AdhocFilters, force: boolean = false) {
		await waitUntil(() => query.isloaded)

		if (!query.doc.operations.length) {
			result.value = { ...EMPTY_RESULT }
			return
		}

		const executionId = JSON.stringify({
			operations: currentOperations.value,
			adhoc_filters: adhocFilters,
		})

		if (!force && lastExecutionId === executionId) {
			return Promise.resolve()
		}

		executing.value = true
		return query
			.call('execute', {
				active_operation_idx: activeOperationIdx.value,
				adhoc_filters: adhocFilters,
			})
			.then((response: any) => {
				lastExecutionId = executionId

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
			.catch((e: Error) => {
				result.value = { ...EMPTY_RESULT }
				showErrorToast(e)
			})
			.finally(() => {
				executing.value = false
			})
	}

	const fetchingCount = ref(false)
	async function fetchResultCount() {
		await waitUntil(() => query.isloaded)

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
			.catch(showErrorToast)
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
			currentOperations.value[existingOrderByIndex] = order_by(args)
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
			max: 100,
			debounce: 500,
		}
	)

	const autoExecute = ref(false)
	let stopAutoExecute: Function
	wheneverChanges(
		autoExecute,
		() => {
			if (autoExecute.value && !stopAutoExecute) {
				stopAutoExecute = wheneverChanges(currentOperations, () => autoExecute.value && execute(), {
					immediate: true,
					deep: true,
				})
			} else {
				stopAutoExecute?.()
			}
		},
		{ immediate: true }
	)

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

		dimensions,
		measures,
		getDimension,
		getMeasure,

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
}

function getQueryResource(name: string) {
	const doctype = 'Insights Query v3'
	const query = useDocumentResource<InsightsQueryv3>(doctype, name, {
		initialDoc: { ...INITIAL_DOC, name },
		enableAutoSave: true,
		disableLocalStorage: true,
		transform: transformQueryDoc,
	})
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
