<script setup lang="ts">
import { computed, inject, ref } from 'vue'
import { FIELDTYPES } from '../../helpers/constants'
import {
	aggregations,
	ColumnMeasure,
	Dimension,
	DimensionDataType,
	MeasureDataType,
	QueryResultColumn,
	SummarizeArgs,
} from '../../types/query.types'
import { Query } from '../query'

const props = defineProps<{
	summary?: SummarizeArgs
}>()
const emit = defineEmits({ select: (args: SummarizeArgs) => true })
const showDialog = defineModel()

const query = inject<Query>('query')!
const columnOptions = ref<QueryResultColumn[]>([])
query.getColumnsForSelection().then((cols: QueryResultColumn[]) => {
	columnOptions.value = cols.map((col) => ({
		...col,
		value: col.name,
	}))
})

const numberColumns = computed(() =>
	columnOptions.value.filter((col) => FIELDTYPES.NUMBER.includes(col.type))
)
const nonNumberColumns = computed(() =>
	columnOptions.value.filter((col) => !FIELDTYPES.NUMBER.includes(col.type))
)

const measures = ref<ColumnMeasure[]>((props.summary?.measures as ColumnMeasure[]) || [])
const dimensions = ref<Dimension[]>(props.summary?.dimensions || [])

const areAllMeasuresValid = computed(
	() => measures.value.length && measures.value.every((m) => m.column_name)
)
const areAllDimensionsValid = computed(
	() => dimensions.value.length && dimensions.value.every((d) => d.column_name)
)

function addMeasure() {
	measures.value.push({
		measure_name: '',
		column_name: '',
		aggregation: 'sum',
		data_type: 'Decimal',
	})
}
function addDimension() {
	dimensions.value.push({
		column_name: '',
		data_type: 'String',
		granularity: 'month',
	})
}
function resetSelections() {
	measures.value = []
	dimensions.value = []
}
function confirmSelections() {
	console.log('measures', measures.value)
	console.log('dimensions', dimensions.value)
	emit('select', {
		measures: measures.value,
		dimensions: dimensions.value,
	})
	showDialog.value = false
}
</script>

<template>
	<Dialog :modelValue="showDialog" :options="{ size: '2xl' }">
		<template #body>
			<div class="min-w-[36rem] rounded-lg bg-white px-4 pb-6 pt-5 sm:px-6">
				<div class="flex items-center justify-between pb-4">
					<h3 class="text-2xl font-semibold leading-6 text-gray-900">Summarize</h3>
					<Button variant="ghost" @click="showDialog = false" icon="x" size="md">
					</Button>
				</div>
				<div class="flex flex-col gap-4">
					<div class="flex items-start gap-4">
						<span
							class="w-[68px] flex-shrink-0 text-right text-base leading-7 text-gray-600"
							>Aggregate</span
						>
						<div class="flex flex-1 flex-wrap gap-2">
							<div v-for="(measure, idx) in measures" :key="idx" class="flex">
								<Autocomplete
									button-classes="rounded-r-none"
									placeholder="Agg"
									:options="aggregations"
									:modelValue="measure.aggregation"
									@update:modelValue="measure.aggregation = $event.value"
									:hide-search="true"
								/>
								<Autocomplete
									button-classes="rounded-l-none"
									:placeholder="measure.aggregation"
									:options="columnOptions"
									:modelValue="measure.column_name"
									@update:model-value="(e: QueryResultColumn) => {
										measure.column_name = e.name
										measure.data_type = e.type as MeasureDataType
										measure.measure_name = `${measure.aggregation}(${e.name})`
									}"
								/>
							</div>
							<Button icon="plus" @click="addMeasure"> </Button>
						</div>
					</div>
					<div class="flex items-start gap-4">
						<span
							class="w-[68px] flex-shrink-0 text-right text-base leading-7 text-gray-600"
						>
							Group By
						</span>
						<div class="flex flex-1 flex-wrap gap-2">
							<div v-for="(dimension, idx) in dimensions" :key="idx" class="flex">
								<Autocomplete
									placeholder="Column"
									:options="nonNumberColumns"
									:modelValue="dimension.column_name"
									@update:model-value="(e: QueryResultColumn) => {
										dimension.column_name = e.name
										dimension.data_type = e.type as DimensionDataType
									}"
								/>
							</div>
							<Button icon="plus" @click="addDimension"> </Button>
						</div>
					</div>
					<div class="mt-2 flex justify-end">
						<div class="flex gap-2">
							<Button label="Clear" variant="outline" @click="resetSelections" />
							<Button
								label="Done"
								variant="solid"
								:disabled="!areAllMeasuresValid || !areAllDimensionsValid"
								@click="confirmSelections"
							/>
						</div>
					</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>
