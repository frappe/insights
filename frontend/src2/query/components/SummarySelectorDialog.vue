<script setup lang="ts">
import { computed, inject, ref, watchEffect } from 'vue'
import DimensionPicker from '../../charts/components/DimensionPicker.vue'
import MeasurePicker from '../../charts/components/MeasurePicker.vue'
import { copy } from '../../helpers'
import {
	ColumnMeasure,
	ColumnOption,
	Dimension,
	DimensionOption,
	MeasureOption,
	QueryResultColumn,
	SummarizeArgs,
} from '../../types/query.types'
import { getDimensions, getMeasures } from '../helpers'
import { Query } from '../query'

const props = defineProps<{
	summary?: SummarizeArgs
}>()
const emit = defineEmits({ select: (args: SummarizeArgs) => true })
const showDialog = defineModel()

const query = inject<Query>('query')!
const columnOptions = ref<QueryResultColumn[]>([])
query.getColumnsForSelection().then((cols: ColumnOption[]) => {
	columnOptions.value = cols.map((col) => {
		return {
			name: col.value,
			type: col.data_type,
		}
	})
})

const dimensionOptions = computed<DimensionOption[]>(() => {
	const _dimensions = getDimensions(columnOptions.value)
	return _dimensions.map((dimension) => ({
		...dimension,
		label: dimension.column_name,
		value: dimension.column_name,
	}))
})

const measureOptions = computed<MeasureOption[]>(() => {
	const _measures = getMeasures(columnOptions.value)
	return _measures.map((measure) => ({
		...measure,
		label: measure.measure_name,
		value: measure.measure_name,
	}))
})

const measures = ref<ColumnMeasure[]>([])
const dimensions = ref<Dimension[]>([])

if (props.summary?.measures) {
	measures.value = copy(props.summary.measures as ColumnMeasure[])
}
if (props.summary?.dimensions) {
	dimensions.value = copy(props.summary.dimensions)
}

watchEffect(() => {
	if (!measures.value.length) {
		addMeasure()
	}
	if (!dimensions.value.length) {
		addDimension()
	}
})

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
		dimension_name: '',
	})
}
function resetSelections() {
	measures.value = []
	dimensions.value = []
}
function confirmSelections() {
	emit('select', {
		measures: measures.value.filter((m) => m.column_name),
		dimensions: dimensions.value.filter((d) => d.column_name),
	})
	showDialog.value = false
}
</script>

<template>
	<Dialog :modelValue="showDialog" :options="{ size: '2xl' }">
		<template #body>
			<div class="min-w-[36rem] rounded-lg bg-white px-4 pb-6 pt-5 text-base sm:px-6">
				<div class="flex items-center justify-between pb-4">
					<h3 class="text-2xl font-semibold leading-6 text-gray-900">Summarize</h3>
					<Button variant="ghost" @click="showDialog = false" icon="x" size="md">
					</Button>
				</div>
				<div class="flex flex-col gap-4">
					<div class="flex gap-4">
						<div class="flex-1 flex-shrink-0">
							<p class="mb-1.5 text-gray-600">Group By</p>
							<div class="flex flex-col gap-2">
								<DimensionPicker
									v-for="(dimension, idx) in dimensions"
									:key="idx"
									v-model="dimensions[idx]"
									:options="dimensionOptions"
									@remove="dimensions.splice(idx, 1)"
								/>
							</div>
							<button
								class="mt-1.5 text-left text-xs text-gray-600 hover:underline"
								@click="addDimension"
							>
								+ Add
							</button>
						</div>
						<div class="flex-1 flex-shrink-0">
							<p class="mb-1.5 text-gray-600">Aggregate</p>
							<div class="flex flex-col gap-2">
								<MeasurePicker
									v-for="(measure, idx) in measures"
									:key="idx"
									v-model="measures[idx]"
									:options="measureOptions"
									@remove="measures.splice(idx, 1)"
								/>
							</div>
							<button
								class="mt-1.5 text-left text-xs text-gray-600 hover:underline"
								@click="addMeasure"
							>
								+ Add
							</button>
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
