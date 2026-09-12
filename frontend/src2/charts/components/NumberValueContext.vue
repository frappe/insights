<script setup lang="ts">
import { computed } from 'vue'
import InlineFormControlLabel from '../../components/InlineFormControlLabel.vue'
import { __ } from '../../translation'
import type { NumberChartConfig, NumberComparison, NumberTarget } from '../../types/chart.types'
import type { ColumnOption, Dimension, Measure } from '../../types/query.types'
import type { NumberPeriod } from '../window'
import { defaultComparisonLabel } from '../adapter/number'
import MeasurePicker from './MeasurePicker.vue'

// What a reading is read against: the target it aims at, and the one number it
// is compared with. Two blocks because a card reads them in two places — the
// target on the value line, the comparison in the delta row — and a reader who
// wants a second comparison wants a second card.

const props = defineProps<{
	columnOptions: ColumnOption[]
	/** The period the chart reads, when it reads one. Both period choices need it. */
	period?: NumberPeriod
	/** The chart's date column, which words a `previous` comparison. */
	dateColumn?: Dimension
}>()
const emit = defineEmits({ 'dialog-open': () => true })
const target = defineModel<NumberTarget | undefined>('target')
const comparison = defineModel<NumberComparison | undefined>('comparison')

const targetSourceOptions = [
	{ label: __('None'), value: 'none' },
	{ label: __('Number'), value: 'constant' },
	{ label: __('Measure'), value: 'measure' },
]

// Listed even when they cannot be picked. A list that changed shape under the
// author would hide the dependency. A disabled row states it, and the remedy is
// one section up.
const comparisonSourceOptions = computed(() => [
	{ label: __('None'), value: 'none' },
	{ label: __('Previous period'), value: 'previous', disabled: !props.period },
	// A year back is the same span anchored a year earlier, which only a span
	// names. A grain period would have to count rows back instead, and a gap in
	// the data would make it count the wrong one.
	{ label: __('Same period last year'), value: 'last year', disabled: !props.period?.span },
	{ label: __('Number'), value: 'constant' },
	{ label: __('Measure'), value: 'measure' },
])

// The caption the card prints when the author types none. Shown as the field's
// placeholder, the same rule the format fields follow for prefix and suffix.
const captionPlaceholder = computed(() => {
	if (!comparison.value) return ''
	const config = { date_column: props.dateColumn, window: props.period } as NumberChartConfig
	return defaultComparisonLabel(comparison.value, config) || ''
})

const showOptions = [
	{ label: __('% change'), value: 'change' },
	{ label: __('Difference'), value: 'delta' },
]

const targetSource = computed(() => {
	if (!target.value) return 'none'
	return target.value.measure ? 'measure' : 'constant'
})

function setTargetSource(source: string) {
	// The old source's field named the old source's number, so it goes with it.
	if (source === 'none') target.value = undefined
	else if (source === 'measure') target.value = { measure: blankMeasure() }
	else target.value = {}
}

const comparisonSource = computed(() => comparison.value?.source || 'none')

function setComparisonSource(source: string) {
	if (source === 'none') {
		comparison.value = undefined
		return
	}

	// The stored comparison is the question alone, so a period changed under it
	// keeps answering the same one — how it is fetched is decided where it is
	// read, off the period the card holds then.
	comparison.value = {
		source: source as NumberComparison['source'],
		show: comparison.value?.show || 'change',
		...(comparison.value?.label ? { label: comparison.value.label } : {}),
		...(source === 'measure' ? { measure: blankMeasure() } : {}),
	}
}

// The picker reads and writes the stored measure itself, so the aggregation it
// sets in place lands on the config.
const targetMeasure = computed<Measure>({
	get: () => target.value?.measure as Measure,
	set: (measure) => (target.value = { ...target.value, measure }),
})

const comparisonMeasure = computed<Measure>({
	get: () => comparison.value?.measure as Measure,
	set: (measure) => comparison.value && (comparison.value.measure = measure),
})

/**
 * A blank measure, for the author to state the fold in. The base query is at
 * base grain and the chart folds it, so a column picked without a function
 * would have to be summed by default — and a sum of a period-grain target, one
 * monthly budget repeated over the month's rows, counts it once per row.
 */
function blankMeasure(): Measure {
	return { column_name: '', data_type: 'Decimal', measure_name: '', aggregation: '' }
}
</script>

<template>
	<div class="flex flex-col gap-2">
		<InlineFormControlLabel label="Target">
			<FormControl
				type="select"
				:options="targetSourceOptions"
				:modelValue="targetSource"
				@update:modelValue="setTargetSource($event)"
			/>
		</InlineFormControlLabel>

		<div v-if="targetSource === 'constant'" class="pl-[30%]">
			<FormControl
				type="number"
				autocomplete="off"
				:modelValue="target?.value"
				@update:modelValue="target = { value: $event === '' ? undefined : Number($event) }"
			/>
		</div>

		<div v-if="targetSource === 'measure'" class="pl-[30%]">
			<MeasurePicker
				v-model="targetMeasure"
				:column-options="columnOptions"
				@remove="target = undefined"
				@dialog-open="emit('dialog-open')"
			/>
		</div>

		<InlineFormControlLabel label="Compare with">
			<FormControl
				type="select"
				:options="comparisonSourceOptions"
				:modelValue="comparisonSource"
				@update:modelValue="setComparisonSource($event)"
			/>
		</InlineFormControlLabel>

		<div v-if="comparison?.source === 'constant'" class="pl-[30%]">
			<FormControl
				type="number"
				autocomplete="off"
				:modelValue="comparison.value"
				@update:modelValue="comparison.value = $event === '' ? undefined : Number($event)"
			/>
		</div>

		<div v-if="comparison?.source === 'measure'" class="pl-[30%]">
			<MeasurePicker
				v-model="comparisonMeasure"
				:column-options="columnOptions"
				@remove="comparison = undefined"
				@dialog-open="emit('dialog-open')"
			/>
		</div>

		<template v-if="comparison">
			<div class="pl-[30%]">
				<FormControl
					type="select"
					:options="showOptions"
					:modelValue="comparison.show || 'change'"
					@update:modelValue="comparison.show = $event"
				/>
			</div>

			<div class="pl-[30%]">
				<FormControl
					autocomplete="off"
					:placeholder="captionPlaceholder"
					:modelValue="comparison.label"
					@update:modelValue="comparison.label = $event || undefined"
				/>
			</div>
		</template>
	</div>
</template>
