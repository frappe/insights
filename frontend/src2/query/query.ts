import { FIELDTYPES, wheneverChanges } from '@/utils'
import { confirmDialog } from '@/utils/components'
import { call } from 'frappe-ui'
import { computed, reactive } from 'vue'
import { WorkbookQuery } from '../workbook/workbook'
import {
	cast,
	column,
	count,
	expression,
	filter,
	get_date_format,
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
	table,
} from './helpers'

const queries = new Map<string, Query>()
export function getCachedQuery(name: string) {
	return queries.get(name)
}

export default function useQuery(workbookQuery: WorkbookQuery) {
	const existingQuery = queries.get(workbookQuery.name)
	if (existingQuery) return existingQuery

	const query = makeQuery(workbookQuery)
	queries.set(workbookQuery.name, query)
	return query
}

function makeQuery(workbookQuery: WorkbookQuery) {
	const query = reactive({
		doc: workbookQuery,

		activeOperationIdx: -1,
		currentOperations: computed(() => [] as Operation[]),

		autoExecute: true,
		executing: false,
		result: {} as QueryResult,

		execute,
		setOperations,
		setActiveStep,
		removeStep,
		setSource,
		addSource,
		addJoin,
		addFilter,
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
		changeDateGranularity,

		getDistinctColumnValues,

		dimensions: computed(() => ({} as Dimension[])),
		measures: computed(() => ({} as Measure[])),
		getDimension,
		getMeasure,
	})

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
		} else {
			query.activeOperationIdx = operations.length - 1
		}
		return operations
	})

	wheneverChanges(
		() => query.currentOperations,
		() => query.autoExecute && execute(),
		{ deep: true, immediate: true }
	)
	async function execute() {
		if (!query.doc.operations.length) {
			query.result = {
				executedSQL: '',
				totalRowCount: 0,
				rows: [],
				columns: [],
				columnOptions: [],
			}
			return
		}

		query.executing = true
		return call(
			'insights.insights.doctype.insights_workbook.insights_workbook.fetch_query_results',
			{
				operations: query.doc.operations,
			}
		)
			.then((response: any) => {
				if (!response) return
				query.result.executedSQL = response.sql
				query.result.columns = response.columns
				query.result.rows = response.rows.map((row: any) =>
					Object.fromEntries(query.result.columns.map((column, idx) => [column.name, row[idx]]))
				)
				query.result.totalRowCount = response.total_row_count
				query.result.columnOptions = query.result.columns.map((column) => ({
					label: column.name,
					value: column.name,
					description: column.type,
					data_type: column.type,
				}))
			})
			.finally(() => {
				query.executing = false
			})
	}

	function setActiveStep(index: number) {
		query.activeOperationIdx = index
	}

	function removeStep(index: number) {
		query.doc.operations.splice(index, 1)
		if (query.activeOperationIdx >= index) {
			query.activeOperationIdx--
		}
		if (query.activeOperationIdx < 0) {
			query.activeOperationIdx = -1
		}
	}

	type setSourceArgs = { table: string; data_source: string }
	function setSource(args: setSourceArgs) {
		const _setSource = () => {
			query.setOperations([])
			query.addSource({
				table: table(args.data_source, args.table),
			})
			query.doc.title = args.table
		}
		if (!query.doc.operations.length) {
			_setSource()
			return
		}
		confirmDialog({
			title: 'Change Source',
			message: 'Changing the source will clear the current pipeline. Please confirm.',
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
		addOperation(join(args))
	}

	function addFilter(args: FilterArgs | FilterArgs[]) {
		if (!Array.isArray(args)) args = [args]
		args.forEach((arg) => addOperation(filter(arg)))
	}

	function addMutate(args: MutateArgs) {
		addOperation(mutate(args))
	}

	function addSummarize(args: SummarizeArgs) {
		addOperation(summarize(args))
	}

	function addOrderBy(args: OrderByArgs) {
		const existingOrderBy = query.doc.operations.find(
			(op) =>
				op.type === 'order_by' &&
				op.column.column_name === args.column.column_name &&
				op.direction === args.direction
		)
		if (existingOrderBy) return

		const existingOrderByIndex = query.doc.operations.findIndex(
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

	function selectColumns(columns: string[]) {
		addOperation(select({ column_names: columns }))
	}

	function renameColumn(oldName: string, newName: string) {
		addOperation(
			rename({
				column: column(oldName),
				new_name: newName,
			})
		)
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
			})
		)
	}

	function changeDateGranularity(column_name: string, newGranularity: GranularityType) {
		const dateFormat = get_date_format(newGranularity)
		addOperation(
			mutate({
				data_type: 'Date',
				new_name: column_name,
				mutation: expression(`q.${column_name}.strftime('${dateFormat}')`),
			})
		)
	}

	function setOperations(newOperations: Operation[]) {
		query.doc.operations = newOperations
		query.activeOperationIdx = newOperations.length - 1
	}

	function getDistinctColumnValues(column: string, search_term: string = '') {
		return call(
			'insights.insights.doctype.insights_workbook.insights_workbook.get_distinct_column_values',
			{
				operations: query.doc.operations,
				column_name: column,
				search_term,
			}
		)
	}

	function getDimension(column_name: string) {
		return query.dimensions.find((d) => d.column_name === column_name)
	}

	function getMeasure(column_name: string) {
		return query.measures.find((m) => m.column_name === column_name)
	}

	return query
}

export type Query = ReturnType<typeof makeQuery>
