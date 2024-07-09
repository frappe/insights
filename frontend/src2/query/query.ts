import { FIELDTYPES } from '@/utils'
import { watchDebounced, watchOnce } from '@vueuse/core'
import { call } from 'frappe-ui'
import { computed, reactive } from 'vue'
import { copy, showErrorToast } from '../helpers'
import { confirmDialog } from '../helpers/confirm_dialog'
import {
	ColumnDataType,
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
	Rename,
	SelectArgs,
	SourceArgs,
	SummarizeArgs,
} from '../types/query.types'
import { WorkbookQuery } from '../types/workbook.types'
import {
	cast,
	column,
	count,
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
	summarize,
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
		currentOperations: computed(() => [] as Operation[]),
		activeEditIndex: -1,
		activeEditOperation: computed(() => ({}) as Operation),

		autoExecute: true,
		executing: false,
		result: {} as QueryResult,

		execute,
		setOperations,
		setActiveStep,
		setActiveEditIndex,
		removeStep,
		setSource,
		addSource,
		addJoin,
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

		getDistinctColumnValues,
		getColumnsForSelection,

		dimensions: computed(() => ({}) as Dimension[]),
		measures: computed(() => ({}) as Measure[]),
		getDimension,
		getMeasure,

		reset,
	})

	watchOnce(
		() => query.doc.operations.length,
		() => (query.activeOperationIdx = query.doc.operations.length - 1),
		{ immediate: true },
	)

	// @ts-ignore
	query.dimensions = computed(() => {
		if (!query.result.columns?.length) return []
		return query.result.columns
			.filter((column) => FIELDTYPES.DIMENSION.includes(column.type))
			.map((column) => ({
				column_name: column.name,
				data_type: column.type as DimensionDataType,
				granularity: FIELDTYPES.DATE.includes(column.type) ? 'month' : undefined,
			}))
	})
	// @ts-ignore
	query.measures = computed(() => {
		if (!query.result.columns?.length) return []
		const count_measure = count()
		return [
			count_measure,
			...query.result.columns
				.filter((column) => FIELDTYPES.MEASURE.includes(column.type))
				.map((column) => ({
					column_name: column.name,
					data_type: column.type as MeasureDataType,
					aggregation: 'sum',
				})),
		]
	})

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

	watchDebounced(
		() => query.currentOperations,
		() => query.autoExecute && execute(),
		{ deep: true, immediate: true },
	)

	async function execute() {
		if (!query.doc.operations.length) {
			query.result = {
				executedSQL: '',
				totalRowCount: 0,
				rows: [],
				formattedRows: [],
				columns: [],
				columnOptions: [],
			}
			return
		}

		query.executing = true
		return call(
			'insights.insights.doctype.insights_workbook.insights_workbook.fetch_query_results',
			{
				use_live_connection: query.doc.use_live_connection,
				operations: query.currentOperations,
			},
		)
			.then((response: any) => {
				if (!response) return
				query.result.executedSQL = response.sql
				query.result.columns = response.columns
				query.result.rows = response.rows.map((row: any) =>
					Object.fromEntries(query.result.columns.map((column, idx) => [column.name, row[idx]])),
				)
				query.result.formattedRows = getFormattedRows(query)
				query.result.totalRowCount = response.total_row_count
				query.result.columnOptions = query.result.columns.map((column) => ({
					label: column.name,
					value: column.name,
					description: column.type,
					query: query.doc.name,
					data_type: column.type,
				}))
			})
			.catch(showErrorToast)
			.finally(() => {
				query.executing = false
			})
	}

	function setActiveStep(index: number) {
		query.activeOperationIdx = index
		query.activeEditIndex = -1
	}

	function setActiveEditIndex(index: number) {
		query.activeEditIndex = index
	}

	function removeStep(index: number) {
		query.doc.operations.splice(index, 1)
		switch (true) {
			case query.activeOperationIdx === index && index > 0:
				// if the active operation is removed, move the active operation to the previous step
				query.activeOperationIdx--
				break
			case query.activeOperationIdx === index && index === 0:
				// if the first operation is removed, reset the active operation
				query.activeOperationIdx = -1
				break
			default:
				break
		}
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
		addOperation(summarize(args))
	}

	function addOrderBy(args: OrderByArgs) {
		const existingOrderBy = query.doc.operations.find(
			(op) =>
				op.type === 'order_by' &&
				op.column.column_name === args.column.column_name &&
				op.direction === args.direction,
		)
		if (existingOrderBy) return

		const existingOrderByIndex = query.doc.operations.findIndex(
			(op) => op.type === 'order_by' && op.column.column_name === args.column.column_name,
		)
		if (existingOrderByIndex > -1) {
			query.doc.operations[existingOrderByIndex] = order_by(args)
		} else {
			addOperation(order_by(args))
		}
	}

	function removeOrderBy(column_name: string) {
		const index = query.doc.operations.findIndex(
			(op) => op.type === 'order_by' && op.column.column_name === column_name,
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
		const existingRenameIdx = query.doc.operations.findIndex(
			(op) => op.type === 'rename' && op.new_name === oldName,
		)
		if (existingRenameIdx > -1) {
			const existingRename = query.doc.operations[existingRenameIdx] as Rename
			existingRename.new_name = newName
		}

		// if not, add a new rename operation
		else {
			addOperation(
				rename({
					column: column(oldName),
					new_name: newName,
				}),
			)
		}
	}

	function removeColumn(column_names: string | string[]) {
		if (!Array.isArray(column_names)) column_names = [column_names]
		addOperation(remove({ column_names }))
	}

	function changeColumnType(column_name: string, newType: ColumnDataType) {
		addOperation(
			cast({
				column: column(column_name),
				data_type: newType,
			}),
		)
	}

	function setOperations(newOperations: Operation[]) {
		query.doc.operations = newOperations
		query.activeOperationIdx = newOperations.length - 1
	}

	function getDistinctColumnValues(column: string, search_term: string = '') {
		const operations =
			query.activeEditIndex > -1
				? // when editing a filter, get distinct values from the operations before the filter
					query.doc.operations.slice(0, query.activeEditIndex)
				: query.currentOperations

		return call(
			'insights.insights.doctype.insights_workbook.insights_workbook.get_distinct_column_values',
			{
				use_live_connection: query.doc.use_live_connection,
				operations: operations,
				column_name: column,
				search_term,
			},
		)
	}

	function getColumnsForSelection() {
		const operations =
			query.activeEditOperation.type === 'select'
				? query.doc.operations.slice(0, query.activeEditIndex)
				: query.currentOperations

		const method =
			'insights.insights.doctype.insights_workbook.insights_workbook.get_columns_for_selection'
		return call(method, {
			use_live_connection: query.doc.use_live_connection,
			operations,
		})
	}

	function getDimension(column_name: string) {
		return query.dimensions.find((d) => d.column_name === column_name)
	}

	function getMeasure(column_name: string) {
		return query.measures.find((m) => m.column_name === column_name)
	}

	const originalQuery = copy(workbookQuery)
	function reset() {
		query.doc = copy(originalQuery)
		query.activeOperationIdx = -1
		query.autoExecute = true
		query.executing = false
		query.result = {} as QueryResult
	}

	return query
}

export type Query = ReturnType<typeof makeQuery>
