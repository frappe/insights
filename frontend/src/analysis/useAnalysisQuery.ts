import { DataModel, Dimension, Measure } from '@/datamodel/useDataModel'
import { QueryResultColumn, QueryResultRow } from '@/query/next/useQuery'
import { call } from 'frappe-ui'
import { reactive } from 'vue'
import storeLocally from './storeLocally'

export function useAnalysisQuery(name: string, dataModel: DataModel) {
	const query = reactive({
		name,
		title: '',
		rows: [] as Dimension[],
		columns: [] as Dimension[],
		values: [] as Measure[],
		filters: [],
		sort_order: [],
		limit: 100,

		result: {
			columns: [] as QueryResultColumn[],
			rows: [] as QueryResultRow[],
		},

		addRow,
		addColumn,
		addValue,
		reset,

		executing: false,
		execute,

		serialize() {
			return {
				name: query.name,
				title: query.title,
				rows: query.rows,
				columns: query.columns,
				values: query.values,
				filters: query.filters,
				sort_order: query.sort_order,
				limit: query.limit,
				result: query.result,
			}
		},
	})


	const storedQuery = storeLocally<AnalysisQuerySerialized>({
		key: 'name',
		namespace: 'insights:analysis-query:',
		serializeFn: query.serialize,
		defaultValue: {} as AnalysisQuerySerialized,
	})
	if (storedQuery.value.name === query.name) {
		Object.assign(query, storedQuery.value)
	}

	function addRow(dimension: Dimension) {
		const existing = query.rows.find((d) => d.column_name === dimension.column_name)
		if (existing) return
		query.rows.push(dimension)
	}

	function addColumn(dimension: Dimension) {
		const existing = query.columns.find((d) => d.column_name === dimension.column_name)
		if (existing) return
		query.columns.push(dimension)
	}

	function addValue(measure: Measure) {
		const existing = query.values.find((m) => m.column_name === measure.column_name)
		if (existing) return
		query.values.push(measure)
	}

	function reset() {
		query.rows = []
		query.columns = []
		query.values = []
		query.filters = []
		query.sort_order = []
		query.limit = 100
		query.result.columns = []
		query.result.rows = []
	}

	function execute() {
		query.executing = true
		return call('insights.api.queries.execute_analysis_query', {
			model: dataModel,
			query: query.serialize(),
		})
			.then((response: any) => {
				query.result.rows = response.rows
				query.result.columns = response.columns
			})
			.catch((error: any) => {
				console.error(error)
			})
			.finally(() => {
				query.executing = false
			})
	}

	return query
}

export type AnalysisQuery = ReturnType<typeof useAnalysisQuery>
export type AnalysisQuerySerialized = ReturnType<AnalysisQuery['serialize']>
export const analysisQueryKey = Symbol('analysisQuery')