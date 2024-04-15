import { wheneverChanges } from '@/utils'
import { confirmDialog } from '@/utils/components'
import { call } from 'frappe-ui'
import { computed, reactive } from 'vue'
import {
	cast,
	column,
	filter,
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
} from './query_utils'
import { useStorage, watchDebounced } from '@vueuse/core'

export type QueryResultColumn = { name: string; type: ColumnDataType }
export type QueryResultRow = any[]
export type QueryResult = {
	executedSQL: string
	totalRowCount: number
	rows: QueryResultRow[]
	columns: QueryResultColumn[]
	columnOptions: DropdownOption[]
}

export type QuerySerialized = {
	name: string
	dataSource: string
	operations: Operation[]
	activeOperationIdx: number
	result: QueryResult
}
function useQuery(name: string) {
	const query = reactive({
		name,
		dataSource: '',

		operations: [] as Operation[],
		activeOperationIdx: -1,
		currentOperations: computed(() => [] as Operation[]),

		executing: false,
		result: {
			executedSQL: '',
			totalRowCount: 0,
			rows: [],
			columns: [],
			columnOptions: [],
		} as QueryResult,

		showSourceSelectorDialog: false,
		showColumnsSelectorDialog: false,
		showFiltersSelectorDialog: false,
		showNewColumnSelectorDialog: false,
		showJoinSelectorDialog: false,

		execute,
		setOperations,
		setActiveStep,
		removeStep,
		setSource,
		setDataSource,
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

		getDistinctColumnValues,
		getMinAndMax,

		serialize(): QuerySerialized {
			return {
				name: query.name,
				dataSource: query.dataSource,
				operations: query.operations,
				activeOperationIdx: query.activeOperationIdx,
				result: query.result,
			}
		},
	})

	const storedQuery = useStorage(`insights:query:${name}`, {} as QuerySerialized)
	if (storedQuery.value.name === name) {
		Object.assign(query, storedQuery.value)
	}
	watchDebounced(query, () => (storedQuery.value = query.serialize()), {
		deep: true,
		debounce: 1000,
	})

	// @ts-ignore
	query.currentOperations = computed(() => {
		const operations = [...query.operations]
		if (query.activeOperationIdx >= 0) {
			operations.splice(query.activeOperationIdx + 1)
		}
		return operations
	})

	wheneverChanges(() => query.currentOperations, execute, { deep: true })
	function execute() {
		if (!query.dataSource) throw new Error('Data source not set')
		if (!query.operations.length) {
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
		return call('insights.api.queries.execute_query_pipeline', {
			data_source: query.dataSource,
			query_pipeline: query.currentOperations,
		})
			.then((response: any) => {
				query.result.executedSQL = response.sql
				query.result.rows = response.rows
				query.result.columns = response.columns
				query.result.totalRowCount = response.total_row_count
				query.result.columnOptions = query.result.columns.map((column) => ({
					label: column.name,
					value: column.name,
					description: column.type,
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
		query.operations.splice(index, 1)
		if (query.activeOperationIdx >= index) {
			query.activeOperationIdx--
		}
		if (query.activeOperationIdx < 0) {
			query.activeOperationIdx = -1
		}
	}

	type setSourceArgs = { table: string; data_source: string } | { pipeline: QuerySerialized }

	function setSource(args: setSourceArgs) {
		const _setSource = () => {
			query.setOperations([])
			if ('pipeline' in args) {
				query.setDataSource(args.pipeline.dataSource)
				query.setOperations(args.pipeline.operations)
			} else {
				query.setDataSource(args.data_source)
				query.addSource({ table: table(args.table) })
			}
		}
		if (!query.dataSource || !query.operations.length) {
			_setSource()
			return
		}
		confirmDialog({
			title: 'Change Source',
			message: 'Changing the source will clear the current pipeline. Please confirm.',
			onSuccess: _setSource,
		})
	}

	function setDataSource(data_source: string) {
		query.dataSource = data_source
	}

	function addOperation(op: Operation) {
		query.operations.splice(query.activeOperationIdx + 1, 0, op)
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
		const existingOrderBy = query.operations.find(
			(op) =>
				op.type === 'order_by' &&
				op.column.column_name === args.column.column_name &&
				op.direction === args.direction
		)
		if (existingOrderBy) return

		const existingOrderByIndex = query.operations.findIndex(
			(op) => op.type === 'order_by' && op.column.column_name === args.column.column_name
		)
		if (existingOrderByIndex > -1) {
			query.operations[existingOrderByIndex] = order_by(args)
		} else {
			addOperation(order_by(args))
		}
	}

	function removeOrderBy(column_name: string) {
		const index = query.operations.findIndex(
			(op) => op.type === 'order_by' && op.column.column_name === column_name
		)
		if (index > -1) {
			query.operations.splice(index, 1)
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

	function setOperations(newOperations: Operation[]) {
		query.operations = newOperations
		query.activeOperationIdx = newOperations.length - 1
	}

	function getDistinctColumnValues(column: string, search_term: string = '') {
		return call('insights.api.queries.get_distinct_column_values', {
			data_source: query.dataSource,
			query_pipeline: query.currentOperations,
			column_name: column,
			search_term,
		})
	}
	function getMinAndMax(column: string) {
		return call('insights.api.queries.get_min_max', {
			data_source: query.dataSource,
			query_pipeline: query.currentOperations,
			column_name: column,
		})
	}

	return query
}

export type Query = ReturnType<typeof useQuery>
export default useQuery
