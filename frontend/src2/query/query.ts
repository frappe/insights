import { useDebouncedRefHistory, UseRefHistoryReturn } from '@vueuse/core'
import { call } from 'frappe-ui'
import { computed, reactive } from 'vue'
import { copy, showErrorToast, wheneverChanges } from '../helpers'
import { confirmDialog } from '../helpers/confirm_dialog'
import { FIELDTYPES } from '../helpers/constants'
import { createToast } from '../helpers/toasts'
import {
	CodeArgs,
	ColumnDataType,
	CustomOperationArgs,
	Dimension,
	DimensionDataType,
	FilterGroupArgs,
	JoinArgs,
	Measure,
	MeasureDataType,
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
import { WorkbookQuery } from '../types/workbook.types'
import {
	cast,
	column,
	count,
	custom_operation,
	filter_group,
	getFormattedRows,
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
	code
} from './helpers'

const queries = new Map<string, Query>()
export function getCachedQuery(name: string): Query | undefined {
	return queries.get(name)
}

export default function useQuery(workbookQuery: WorkbookQuery) {
	const existingQuery = queries.get(workbookQuery.name)
	if (existingQuery) return existingQuery

	const query = makeQuery(workbookQuery)
	queries.set(workbookQuery.name, query)
	return query
}

export function makeQuery(workbookQuery: WorkbookQuery) {
	const query = reactive({
		doc: workbookQuery,

		activeOperationIdx: -1,
		activeEditIndex: -1,
		source: computed(() => ''),
		currentOperations: computed(() => [] as Operation[]),
		activeEditOperation: computed(() => ({} as Operation)),

		autoExecute: true,
		executing: false,
		fetchingCount: false,
		result: { ...EMPTY_RESULT },

		getOperationsForExecution,
		execute,
		fetchResultCount,

		setOperations,
		setActiveOperation,
		setActiveEditIndex,
		removeOperation,
		setSource,
		addSource,
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

		dimensions: computed(() => ({} as Dimension[])),
		measures: computed(() => ({} as Measure[])),
		getDimension,
		getMeasure,

		addMeasure,
		updateMeasure,
		removeMeasure,

		reorderOperations,
		reset,

		dashboardFilters: {} as FilterGroupArgs,

		history: {} as UseRefHistoryReturn<any, any>,
		canUndo() {
			return !query.activeEditIndex && !query.executing
		},
		canRedo() {
			return !query.activeEditIndex && !query.executing
		},
	})

	query.activeOperationIdx = query.doc.operations.length - 1

	// @ts-ignore
	query.dimensions = computed(() => {
		if (!query.result.columns?.length) return []
		return query.result.columns
			.filter((column) => FIELDTYPES.DIMENSION.includes(column.type))
			.map((column) => {
				const isDate = FIELDTYPES.DATE.includes(column.type)
				return {
					column_name: column.name,
					data_type: column.type as DimensionDataType,
					granularity: isDate ? 'month' : undefined,
					dimension_name: column.name,
				}
			})
	})

	// @ts-ignore
	query.measures = computed(() => {
		if (!query.result.columns?.length) return []
		const count_measure = count()
		return [
			count_measure,
			...query.result.columns
				.filter((column) => FIELDTYPES.MEASURE.includes(column.type))
				.map((column) => {
					return {
						aggregation: 'sum',
						column_name: column.name,
						measure_name: `sum_of_${column.name}`,
						data_type: column.type as MeasureDataType,
					}
				}),
			...Object.values(query.doc.calculated_measures || {}),
		]
	})

	// @ts-ignore
	query.source = computed(() => {
		const operations = query.getOperationsForExecution()
		return getDataSource(operations)
	})

	function getDataSource(operations: Operation[]): string {
		const source = operations.find((op) => op.type === 'source')
		if (!source) return ''
		if (source.table.type === 'table') {
			return source.table.data_source
		}
		if (source.table.type === 'query' && 'query' in source.table) {
			return getDataSource(source.table.operations!)
		}
		return ''
	}

	// @ts-ignore
	query.currentOperations = computed(() => {
		const operations = [...query.doc.operations]
		if (query.activeOperationIdx >= 0) {
			operations.splice(query.activeOperationIdx + 1)
		}
		return operations
	})

	// @ts-ignore
	query.activeEditOperation = computed(() => {
		if (query.activeEditIndex === -1) return {}
		return query.doc.operations[query.activeEditIndex]
	})

	wheneverChanges(
		() => query.currentOperations,
		() => query.autoExecute && execute(),
		{ deep: true }
	)

	function getOperationsForExecution(): Operation[] {
		if (!query.doc.operations.length) {
			return []
		}

		let _operations = [...query.currentOperations]
		for (const op of _operations) {
			if (op.type !== 'source' && op.type !== 'join' && op.type !== 'union') continue
			if (op.table.type !== 'query') continue

			const queryTable = getCachedQuery(op.table.query_name)
			if (!queryTable) {
				const message = `Query ${op.table.query_name} not found`
				createToast({
					variant: 'error',
					title: 'Error',
					message,
				})
				throw new Error(message)
			}

			op.table.operations = queryTable.getOperationsForExecution()
		}

		if (query.dashboardFilters.filters?.length) {
			_operations.push(filter_group(query.dashboardFilters))
			query.dashboardFilters = {} as FilterGroupArgs
		}

		return _operations
	}

	async function execute() {
		if (!query.doc.operations.length) {
			query.result = { ...EMPTY_RESULT }
			return
		}

		query.executing = true
		const operations = query.getOperationsForExecution()
		const limit = operations.find((op) => op.type === 'limit')?.limit
		return call('insights.api.workbooks.fetch_query_results', {
			use_live_connection: query.doc.use_live_connection,
			operations,
			limit,
		})
			.then((response: any) => {
				if (!response) return
				query.result.executedSQL = response.sql
				query.result.columns = response.columns
				query.result.rows = response.rows
				query.result.totalRowCount = 0
				query.result.formattedRows = getFormattedRows(query.result, query.doc.operations)
				query.result.columnOptions = query.result.columns.map((column) => ({
					label: column.name,
					value: column.name,
					description: column.type,
					query: query.doc.name,
					data_type: column.type,
				}))
				query.result.timeTaken = response.time_taken
				query.result.lastExecutedAt = new Date()
			})
			.catch((e: Error) => {
				query.result = { ...EMPTY_RESULT }
				showErrorToast(e)
			})
			.finally(() => {
				query.executing = false
			})
	}

	async function fetchResultCount() {
		if (!query.doc.operations.length) return

		query.fetchingCount = true
		const operations = query.getOperationsForExecution()
		return call('insights.api.workbooks.fetch_query_results_count', {
			use_live_connection: query.doc.use_live_connection,
			operations,
		})
			.then((count: number) => {
				query.result.totalRowCount = count || 0
			})
			.catch(showErrorToast)
			.finally(() => {
				query.fetchingCount = false
			})
	}

	function setActiveOperation(index: number) {
		query.activeOperationIdx = index
		query.activeEditIndex = -1
	}

	function setActiveEditIndex(index: number) {
		query.activeEditIndex = index
	}

	function removeOperation(index: number) {
		query.doc.operations.splice(index, 1)
		if (index > query.activeOperationIdx) return
		query.activeOperationIdx--
		query.activeOperationIdx = Math.max(query.activeOperationIdx, -1)
	}

	function setSource(args: SourceArgs) {
		const editingSource = query.activeEditOperation.type === 'source'

		const _setSource = () => {
			if (editingSource) {
				query.doc.operations[query.activeEditIndex] = source(args)
				query.setActiveEditIndex(-1)
			} else {
				query.setOperations([])
				query.addSource(args)
			}

			if (query.doc.title?.match(/Query \d+/) && 'table_name' in args.table) {
				query.doc.title = args.table.table_name
			}

			if (args.table.type == 'query') {
				const sourceQuery = getCachedQuery(args.table.query_name)
				if (sourceQuery) {
					query.doc.use_live_connection = sourceQuery.doc.use_live_connection
				}
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
		query.doc.operations.splice(query.activeOperationIdx + 1, 0, op)
		query.activeOperationIdx++
	}

	function addSource(args: SourceArgs) {
		addOperation(source(args))
	}

	function addJoin(args: JoinArgs) {
		const editingJoin = query.activeEditOperation.type === 'join'

		if (!editingJoin) {
			addOperation(join(args))
		} else {
			query.doc.operations[query.activeEditIndex] = join(args)
			query.setActiveEditIndex(-1)
		}
	}

	function addUnion(args: UnionArgs) {
		const editingUnion = query.activeEditOperation.type === 'union'

		if (!editingUnion) {
			addOperation(union(args))
		} else {
			query.doc.operations[query.activeEditIndex] = union(args)
			query.setActiveEditIndex(-1)
		}
	}

	function addFilterGroup(args: FilterGroupArgs) {
		const editingFilter =
			query.activeEditOperation.type === 'filter_group' ||
			query.activeEditOperation.type === 'filter'

		if (!editingFilter) {
			addOperation(filter_group(args))
		} else {
			query.doc.operations[query.activeEditIndex] = filter_group(args)
			query.setActiveEditIndex(-1)
		}
	}

	function addMutate(args: MutateArgs) {
		const editingMutate = query.activeEditOperation.type === 'mutate'

		if (!editingMutate) {
			addOperation(mutate(args))
		} else {
			query.doc.operations[query.activeEditIndex] = mutate(args)
			query.setActiveEditIndex(-1)
		}
	}

	function addSummarize(args: SummarizeArgs) {
		const editingSummarize = query.activeEditOperation.type === 'summarize'

		if (!editingSummarize) {
			addOperation(summarize(args))
		} else {
			query.doc.operations[query.activeEditIndex] = summarize(args)
			query.setActiveEditIndex(-1)
		}
	}

	function addOrderBy(args: OrderByArgs) {
		const existingOrderBy = query.currentOperations.find(
			(op) =>
				op.type === 'order_by' &&
				op.column.column_name === args.column.column_name &&
				op.direction === args.direction
		)
		if (existingOrderBy) return

		const existingOrderByIndex = query.currentOperations.findIndex(
			(op) => op.type === 'order_by' && op.column.column_name === args.column.column_name
		)
		if (existingOrderByIndex > -1) {
			query.currentOperations[existingOrderByIndex] = order_by(args)
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
		const editingSelect = query.activeEditOperation.type === 'select'

		if (!editingSelect) {
			addOperation(select(args))
		} else {
			query.doc.operations[query.activeEditIndex] = select(args)
			query.setActiveEditIndex(-1)
		}
	}

	function renameColumn(oldName: string, newName: string) {
		// first check if there's already a rename operation for the column
		const existingRenameIdx = query.currentOperations.findIndex(
			(op) => op.type === 'rename' && op.new_name === oldName
		)
		if (existingRenameIdx > -1) {
			const existingRename = query.currentOperations[existingRenameIdx] as Rename
			existingRename.new_name = newName
		}

		// if not, add a new rename operation
		else {
			addOperation(
				rename({
					column: column(oldName),
					new_name: newName,
				})
			)
		}
	}

	function removeColumn(column_names: string | string[]) {
		if (!Array.isArray(column_names)) {
			column_names = [column_names]
		}

		// if last operation is remove operation, append to it
		const lastOperation = query.doc.operations[query.activeOperationIdx]
		if (lastOperation?.type === 'remove') {
			query.doc.operations[query.activeOperationIdx] = remove({
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
		const editingCustomOperation = query.activeEditOperation.type === 'custom_operation'

		if (!editingCustomOperation) {
			addOperation(custom_operation(args))
		} else {
			query.doc.operations[query.activeEditIndex] = custom_operation(args)
			query.setActiveEditIndex(-1)
		}
	}

	function setOperations(newOperations: Operation[]) {
		query.doc.operations = newOperations
		query.activeOperationIdx = newOperations.length - 1
	}

	function reorderOperations() {
		const sourceOp = query.doc.operations.find((op) => op.type === 'source')
		if (!sourceOp) return

		let newOperations: Operation[] = [sourceOp]
		const opsOrder = [
			'join',
			'mutate',
			'filter_group',
			'filter',
			'select',
			'remove',
			'cast',
			'rename',
			'order_by',
			'limit',
		]
		opsOrder.forEach((opType) => {
			newOperations.push(...query.doc.operations.filter((op) => op.type === opType))
		})

		// combine multiple filter_group & select operations into one
		const filterGroups: FilterGroupArgs[] = []
		const selects: SelectArgs[] = []
		newOperations.forEach((op) => {
			if (op.type === 'filter_group') {
				filterGroups.push(op as FilterGroupArgs)
			} else if (op.type === 'select') {
				selects.push(op as SelectArgs)
			}
		})
		if (filterGroups.length > 1) {
			const index = newOperations.findIndex((op) => op.type === 'filter_group')
			newOperations.splice(
				index,
				filterGroups.length,
				filter_group({
					logical_operator: 'And',
					filters: filterGroups.flatMap((fg) => fg.filters),
				})
			)
		}
		if (selects.length > 1) {
			const index = newOperations.findIndex((op) => op.type === 'select')
			newOperations.splice(
				index,
				selects.length,
				select({
					column_names: selects.flatMap((s) => s.column_names),
				})
			)
		}

		// append all mutated columns & joined columns to the select operation (if not already selected)
		const joinColumns = newOperations
			.filter((op) => op.type === 'join')
			.map((op) => op.select_columns.map((col) => col.column_name))
			.flat()

		const mutatedColumns = newOperations
			.filter((op) => op.type === 'mutate')
			.map((op) => op.new_name)

		const selectOp = newOperations.find((op) => op.type === 'select')
		if (selectOp) {
			const selectArgs = selectOp as SelectArgs
			joinColumns.forEach((column) => {
				if (!selectArgs.column_names.includes(column)) {
					selectArgs.column_names.push(column)
				}
			})
			mutatedColumns.forEach((column) => {
				if (!selectArgs.column_names.includes(column)) {
					selectArgs.column_names.push(column)
				}
			})
		}

		query.setOperations(newOperations)
	}

	function downloadResults() {
		const _downloadResults = () => {
			return call('insights.api.workbooks.download_query_results', {
				use_live_connection: query.doc.use_live_connection,
				operations: query.getOperationsForExecution(),
			}).then((csv_data: string) => {
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
		const operationsForExecution = query.getOperationsForExecution()
		if (query.activeEditIndex > -1) {
			// remove the active edit operation from the operations
			// we can't use activeEditIndex because the operations for execution may have more operations (after query table resolution)
			const idx = operationsForExecution.findIndex((op) => op === query.activeEditOperation)
			operationsForExecution.splice(idx, 1)
		}

		return call('insights.api.workbooks.get_distinct_column_values', {
			use_live_connection: query.doc.use_live_connection,
			operations: operationsForExecution,
			column_name: column,
			search_term,
			limit,
		})
	}

	function getColumnsForSelection() {
		const operationsForExecution = query.getOperationsForExecution()
		if (
			query.activeEditOperation.type === 'select' ||
			query.activeEditOperation.type === 'summarize'
		) {
			// remove the active edit operation from the operations
			const idx = operationsForExecution.findIndex((op) => op === query.activeEditOperation)
			operationsForExecution.splice(idx, 1)
		}

		const method = 'insights.api.workbooks.get_columns_for_selection'
		return call(method, {
			use_live_connection: query.doc.use_live_connection,
			operations: operationsForExecution,
		}).then((columns: QueryResultColumn[]) => {
			return columns.map((column) => ({
				label: column.name,
				value: column.name,
				description: column.type,
				query: query.doc.name,
				data_type: column.type,
			}))
		})
	}

	function getDimension(column_name: string) {
		return query.dimensions.find((d) => d.column_name === column_name)
	}

	function getMeasure(column_name: string) {
		return query.measures.find((m) => m.measure_name === column_name)
	}

	function addMeasure(measure: Measure) {
		query.doc.calculated_measures = {
			...query.doc.calculated_measures,
			[measure.measure_name]: measure,
		}
	}
	function updateMeasure(column_name: string, measure: Measure) {
		if (!query.doc.calculated_measures) query.doc.calculated_measures = {}
		delete query.doc.calculated_measures[column_name]
		query.doc.calculated_measures[measure.measure_name] = measure
	}
	function removeMeasure(column_name: string) {
		if (!query.doc.calculated_measures) return
		delete query.doc.calculated_measures[column_name]
	}

	function getSQLOperation() {
		if (!query.doc.is_native_query) return ''
		return query.doc.operations.find((op) => op.type === 'sql')
	}

	function setSQL(args: SQLArgs) {
		query.doc.operations = []
		if (args.raw_sql.trim().length) {
			query.doc.operations.push(sql(args))
			query.activeOperationIdx = 0
			query.execute()
		} else {
			query.activeOperationIdx = -1
		}
	}

	function getCodeOperation() {
		return query.doc.operations.find((op) => op.type === 'code')
	}

	function setCode(args: CodeArgs) {
		query.doc.operations = []
		if (args.code.trim().length) {
			query.doc.operations.push(code(args))
			query.activeOperationIdx = 0
			query.execute()
		} else {
			query.activeOperationIdx = -1
		}
	}

	const originalQuery = copy(workbookQuery)
	function reset() {
		query.doc = copy(originalQuery)
		query.activeOperationIdx = -1
		query.autoExecute = true
		query.executing = false
		query.result = {} as QueryResult
	}

	query.history = useDebouncedRefHistory(
		// @ts-ignore
		computed({
			get() {
				return {
					doc: query.doc,
					activeOperationIdx: query.activeOperationIdx,
					activeEditIndex: query.activeEditIndex,
				}
			},
			set(value) {
				Object.assign(query.doc, value.doc)
				query.activeOperationIdx = value.activeOperationIdx
				query.activeEditIndex = value.activeEditIndex
			},
		}),
		{
			deep: true,
			max: 100,
			debounce: 500,
		}
	)

	return query
}

const EMPTY_RESULT = {
	executedSQL: '',
	totalRowCount: 0,
	rows: [],
	formattedRows: [],
	columns: [],
	columnOptions: [],
	timeTaken: 0,
	lastExecutedAt: new Date(),
} as QueryResult

export type Query = ReturnType<typeof makeQuery>
