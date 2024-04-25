import storeLocally from '@/analysis/storeLocally'
import useQuery from '@/query/next/useQuery'
import { FIELDTYPES } from '@/utils'
import { computed, reactive } from 'vue'

export default function useDataModel(name: string) {
	const dataModel = reactive({
		name,
		query: useQuery('new-query-1'),

		dimensions: computed(() => [] as Dimension[]),
		measures: computed(() => [] as Measure[]),

		getDimension(name: string) {
			return dataModel.dimensions.find((d) => d.column_name === name)
		},
		getMeasure(name: string) {
			return dataModel.measures.find((m) => m.column_name === name)
		},

		serialize() {
			return {
				name: dataModel.name,
				queryName: dataModel.query.name,
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
			query: useQuery(storedModel.value.queryName),
		})
	}

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
		const countMeasure: Measure = {
			column_name: 'count',
			data_type: 'Integer',
			aggregation: 'count',
		}
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
