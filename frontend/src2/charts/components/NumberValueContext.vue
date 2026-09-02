<script setup lang="ts">
import { computed } from 'vue'
import InlineFormControlLabel from '../../components/InlineFormControlLabel.vue'
import { __ } from '../../translation'
import type { NumberChartConfig, NumberComparison, NumberTarget } from '../../types/chart.types'
import type { ColumnOption, Measure } from '../../types/query.types'
import { LAST_YEAR, previousWindowShift, sameShift, type WindowShift } from '../window'
import MeasurePicker from './MeasurePicker.vue'

// What a reading is read against: the target it aims at, and the one number it
// is compared with. Two blocks because a card reads them in two places — the
// target on the value line, the comparison in the delta row — and a reader who
// wants a second comparison wants a second card.

const props = defineProps<{
	columnOptions: ColumnOption[]
	/** The period the chart reads, when it reads one. Both window choices shift it. */
	window?: NumberChartConfig['window']
}>()
const emit = defineEmits({ 'dialog-open': () => true })
const target = defineModel<NumberTarget | undefined>('target')
const comparison = defineModel<NumberComparison | undefined>('comparison')

const targetSourceOptions = [
	{ label: __('None'), value: 'none' },
	{ label: __('Number'), value: 'constant' },
	{ label: __('Measure'), value: 'measure' },
]

// A window is one of two readings back: the same span a year ago, or the span
// before this one. Both are the chart's own window shifted, so a card with no
// window offers neither.
const SAME_WINDOW_LAST_YEAR = 'window:last year'
const PREVIOUS_WINDOW = 'window:previous'

const comparisonSourceOptions = computed(() => [
	{ label: __('None'), value: 'none' },
	...(props.window?.span
		? [
				{ label: __('Same window last year'), value: SAME_WINDOW_LAST_YEAR },
				{ label: __('Previous window'), value: PREVIOUS_WINDOW },
		  ]
		: []),
	{ label: __('Previous'), value: 'previous' },
	{ label: __('Number'), value: 'constant' },
	{ label: __('Measure'), value: 'measure' },
])

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

/** The choice a stored comparison was written by. */
const comparisonSource = computed(() => {
	const current = comparison.value
	if (!current) return 'none'
	if (current.source !== 'window') return current.source
	// A whole-year window shifts a year back either way, so the two choices write
	// the same comparison. Reading it as the named one keeps the wording steady.
	return sameShift(current.shift, LAST_YEAR) ? SAME_WINDOW_LAST_YEAR : PREVIOUS_WINDOW
})

function setComparisonSource(source: string) {
	if (source === 'none') {
		comparison.value = undefined
		return
	}

	const shifts = source === SAME_WINDOW_LAST_YEAR || source === PREVIOUS_WINDOW
	const shift = shifts ? windowShift(source) : undefined
	comparison.value = {
		source: shifts ? 'window' : (source as NumberComparison['source']),
		...(shift ? { shift } : {}),
		show: comparison.value?.show || 'change',
		...(source === 'measure' ? { measure: blankMeasure() } : {}),
		...(comparison.value?.label ? { label: comparison.value.label } : {}),
	}
}

function windowShift(source: string): WindowShift | undefined {
	if (source === SAME_WINDOW_LAST_YEAR) return { ...LAST_YEAR }
	return previousWindowShift(props.window?.span)
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
					placeholder="vs last month"
					:modelValue="comparison.label"
					@update:modelValue="comparison.label = $event || undefined"
				/>
			</div>
		</template>
	</div>
</template>
