import useQuery from '@/query/next/useQuery'
import { FIELDTYPES } from '@/utils'
import { useStorage, watchDebounced } from '@vueuse/core'
import { computed, reactive } from 'vue'

export default function useDataModel(name: string) {
	const dataModel = reactive({
		name,
		query: useQuery('new-query-1'),

		dimensions: computed(() => [] as Dimension[]),
		measures: computed(() => [] as Measure[]),

		serialize() {
			return {
				name: dataModel.name,
				queryName: dataModel.query.name,
			}
		},
	})

	const storedModel = useStorage(`insights:data-model:${name}`, {} as DataModelSerialized)
	if (storedModel.value.name === name) {
		Object.assign(dataModel, {
			query: useQuery(storedModel.value.queryName),
		})
	}
	watchDebounced(dataModel, () => (storedModel.value = dataModel.serialize()), {
		deep: true,
		debounce: 1000,
	})

	// @ts-ignore
	dataModel.dimensions = computed(() => {
		// TODO: append calculated dimensions
		const resultColumns = dataModel.query.result.columns
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
		const resultColumns = dataModel.query.result.columns
		return resultColumns
			.filter((c) => FIELDTYPES.NUMBER.includes(c.type))
			.map((c) => ({
				column_name: c.name,
				data_type: c.type as MeasureDataType,
				aggregation: 'sum',
			}))
	})

	return dataModel
}

export type DataModel = ReturnType<typeof useDataModel>
export type DataModelSerialized = ReturnType<DataModel['serialize']>

export type Measure = {
	column_name: string
	data_type: MeasureDataType
	aggregation: AggregationType
}
export type Dimension = {
	column_name: string
	data_type: DimensionDataType
	granularity?: GranularityType
}
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
