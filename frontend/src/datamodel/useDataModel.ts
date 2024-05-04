import storeLocally from '@/analysis/storeLocally'
import { count } from '@/query/next/query_utils'
import useQuery, { Query } from '@/query/next/useQuery'
import { FIELDTYPES, wheneverChanges } from '@/utils'
import { call } from 'frappe-ui'
import { computed, reactive } from 'vue'

export default function useDataModel(name: string) {
	const dataModel = reactive({
		name,
		queries: [useQuery('new-query-1')],
		activeQueryIdx: 0,
		activeQuery: computed(() => ({} as Query)),

		dimensions: computed(() => [] as Dimension[]),
		measures: computed(() => [] as Measure[]),
		measureValues: {} as Record<string, any>,

		getDimension(name: string) {
			return dataModel.dimensions.find((d) => d.column_name === name)
		},
		getMeasure(name: string) {
			return dataModel.measures.find((m) => m.column_name === name)
		},

		fetchMeasureValues() {
			if (!dataModel.measures.length) return
			return call('insights.api.queries.get_measure_values', {
				model: dataModel,
				measures: dataModel.measures,
			}).then((res: any) => (dataModel.measureValues = res.rows[0]))
		},

		addQuery() {
			const queryCount = dataModel.queries.length
			const newQuery = useQuery('new-query-' + (queryCount + 1))
			dataModel.queries.push(newQuery)
			dataModel.activeQueryIdx = dataModel.queries.length - 1
		},

		removeQuery(queryName: string) {
			const queryIdx = dataModel.queries.findIndex((q) => q.name === queryName)
			dataModel.queries.splice(queryIdx, 1)
			dataModel.activeQueryIdx = Math.min(queryIdx, dataModel.queries.length - 1)
		},

		setActiveQuery(queryName: string) {
			dataModel.activeQueryIdx = dataModel.queries.findIndex((q) => q.name === queryName)
		},

		serialize() {
			return {
				name: dataModel.name,
				queryNames: dataModel.queries.map((q) => q.name),
			}
		},
	})

	const storedModel = storeLocally<DataModelSerialized>({
		key: 'name',
		namespace: 'insights:data-model:',
		serializeFn: dataModel.serialize,
		defaultValue: {} as DataModelSerialized,
	})
	if (storedModel.value.name === name) {
		Object.assign(dataModel, {
			queries: storedModel.value.queryNames.map((queryName) => useQuery(queryName)),
		})
	}

	// @ts-ignore
	dataModel.activeQuery = computed(() => dataModel.queries[dataModel.activeQueryIdx])

	// @ts-ignore
	dataModel.dimensions = computed(() => {
		// TODO: append calculated dimensions
		const resultColumns = dataModel.queries.flatMap((q) => q.result.columns)
		return resultColumns
			.filter((c) => !FIELDTYPES.NUMBER.includes(c.type))
			.map((c) => ({
				column_name: c.name,
				data_type: c.type as DimensionDataType,
				granularity: FIELDTYPES.DATE.includes(c.type) ? 'month' : undefined,
			}))
	})

	// @ts-ignore
	dataModel.measures = computed(() => {
		// TODO: append calculated measures
		const resultColumns = dataModel.queries.flatMap((q) => q.result.columns)
		const countMeasure: Measure = count()
		return [
			countMeasure,
			...resultColumns
				.filter((c) => FIELDTYPES.NUMBER.includes(c.type))
				.map((c) => ({
					column_name: c.name,
					data_type: c.type as MeasureDataType,
					aggregation: 'sum',
				})),
		]
	})

	// wheneverChanges(() => dataModel.measures, dataModel.fetchMeasureValues, {
	// 	deep: true,
	// 	immediate: true,
	// })

	return dataModel
}

export type DataModel = ReturnType<typeof useDataModel>
export type DataModelSerialized = ReturnType<DataModel['serialize']>
export const dataModelKey = Symbol('dataModel')

export enum DatasetRelationType {
	OneToOne = 'one-to-one',
	OneToMany = 'one-to-many',
	ManyToOne = 'many-to-one',
	ManyToMany = 'many-to-many',
}
export type TableRelationship = {
	leftDataset: string
	rightDataset: string
	leftColumn: string
	rightColumn: string
	relationType: DatasetRelationType
}
