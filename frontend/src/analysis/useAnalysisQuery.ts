import { DataModel, Dimension, Measure } from '@/datamodel/useDataModel'
import { QueryResultColumn, QueryResultRow } from '@/query/next/useQuery'
import { useStorage, watchDebounced } from '@vueuse/core'
import { call } from 'frappe-ui'
import { reactive } from 'vue'

export function useAnalysisQuery(name: string, dataModel: DataModel) {
	const query = reactive({
		name,
		title: '',
		measures: [] as Measure[],
		dimensions: [] as Dimension[],
		filters: [],
		sort_order: [],
		limit: 100,

		addMeasure,
		addDimension,
		remove,

		executing: false,
		execute,

		result: {
			columns: [] as QueryResultColumn[],
			rows: [] as QueryResultRow[],
		},

		serialize() {
			return {
				name: query.name,
				title: query.title,
				measures: query.measures,
				dimensions: query.dimensions,
				filters: query.filters,
				sort_order: query.sort_order,
				limit: query.limit,
				result: query.result,
			}
		},
	})

	const storedQuery = useStorage(
		`insights:analysis-query:${query.name}`,
		{} as AnalysisQuerySerialized
	)
	if (storedQuery.value.name === query.name) {
		Object.assign(query, storedQuery.value)
	}
	watchDebounced(query, () => (storedQuery.value = query.serialize()), {
		deep: true,
		debounce: 1000,
	})

	function addMeasure(measure: Measure) {
		const existing = query.measures.find((m) => m.column_name === measure.column_name)
		if (existing) return
		query.measures.push(measure)
		execute()
	}

	function addDimension(dimension: Dimension) {
		const existing = query.dimensions.find((d) => d.column_name === dimension.column_name)
		if (existing) return
		query.dimensions.push(dimension)
		execute()
	}

	function remove(measureOrDimension: Measure | Dimension) {
		if ('aggregation' in measureOrDimension) {
			query.measures = query.measures.filter((m) => m !== measureOrDimension)
		} else {
			query.dimensions = query.dimensions.filter((d) => d !== measureOrDimension)
		}
		execute()
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