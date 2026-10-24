<script setup lang="ts">
import { computed } from 'vue'
import ColorInput from '../../components/ColorInput.vue'
import InlineFormControlLabel from '../../components/InlineFormControlLabel.vue'
import NumberInput from '../../components/NumberInput.vue'
import { __ } from '../../translation'
import type {
	NumberChartConfig,
	NumberComparison,
	NumberComparisonShow,
	NumberTarget,
} from '../../types/chart.types'
import type { ColumnOption, Dimension, Measure } from '../../types/query.types'
import type { NumberPeriod } from '../window'
import { canDrawProgress, defaultComparisonLabel } from '../adapter/number'
import MeasurePicker from './MeasurePicker.vue'

// What a reading is read against: the target it aims at, with the bar that
// fills towards it, and the one period it is compared with. The target answers
// "compared with what" and the comparison "compared with when". The target
// prints on the value line and the comparison in the delta row. The delta row
// holds one gap, so a target prints its own there only on a reading compared
// with no period.

const props = defineProps<{
	columnOptions: ColumnOption[]
	/** The period the chart reads, when it reads one. Both period choices need it. */
	period?: NumberPeriod
	/** The chart's date column, which words a `previous` comparison. */
	dateColumn?: Dimension
	/** The reading, whose format decides whether a bar has 100% to fill towards. */
	measure?: Measure
}>()
const emit = defineEmits({ 'dialog-open': () => true })
const target = defineModel<NumberTarget | undefined>('target')
const comparison = defineModel<NumberComparison | undefined>('comparison')
const progress = defineModel<boolean | undefined>('progress')
const progressColor = defineModel<string | undefined>('progressColor')
/** Flips the delta row's colors, so it sits with the comparison. */
const negativeIsBetter = defineModel<boolean | undefined>('negativeIsBetter')

const targetSourceOptions = [
	{ label: __('None'), value: 'none' },
	{ label: __('Number'), value: 'constant' },
	{ label: __('Measure'), value: 'measure' },
]

// Listed even when they cannot be picked. A list that changed shape under the
// author would hide the dependency. A disabled row states it, and the remedy is
// one section up: a period, or a target that prints no gap.
const comparisonSourceOptions = computed(() => [
	{ label: __('None'), value: 'none' },
	{
		label: __('Previous period'),
		value: 'previous',
		disabled: !props.period || Boolean(target.value?.gap),
	},
	// A year back is the same span anchored a year earlier, which only a span
	// names. A grain period would have to count rows back instead, and a gap in
	// the data would make it count the wrong one.
	{
		label: __('Same period last year'),
		value: 'last year',
		disabled: !props.period?.span || Boolean(target.value?.gap),
	},
])

// The delta row holds one gap, so a reading compared with a period has no room
// for the target's.
const gapOptions = computed(() => [
	{ label: __('None'), value: 'none' },
	{ label: __('% change'), value: 'change', disabled: Boolean(comparison.value) },
	{ label: __('Difference'), value: 'delta', disabled: Boolean(comparison.value) },
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
	// How the gap prints is not about the number, so it stays.
	const printed = {
		...(target.value?.gap ? { gap: target.value.gap } : {}),
		...(target.value?.label ? { label: target.value.label } : {}),
	}
	if (source === 'none') target.value = undefined
	else if (source === 'measure') target.value = { ...printed, measure: blankMeasure() }
	else target.value = { ...printed }
}

function setTargetValue(value: number | undefined) {
	target.value = { ...target.value, value }
}

function setGap(gap: string) {
	if (!target.value) return
	const next = { ...target.value }
	if (gap === 'none') {
		// The caption names the gap, so it goes when the gap does.
		delete next.gap
		delete next.label
	} else {
		next.gap = gap as NumberComparisonShow
	}
	target.value = next
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
	}
}

// The picker reads and writes the stored measure itself, so the aggregation it
// sets in place lands on the config.
const targetMeasure = computed<Measure>({
	get: () => target.value?.measure as Measure,
	set: (measure) => (target.value = { ...target.value, measure }),
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
	<section class="mt-1 flex flex-col gap-2 border-t pt-3">
		<p class="text-xs-medium text-ink-gray-8">{{ __('Target') }}</p>

		<InlineFormControlLabel :label="__('Target')">
			<FormControl
				type="select"
				:options="targetSourceOptions"
				:modelValue="targetSource"
				@update:modelValue="setTargetSource($event)"
			/>
		</InlineFormControlLabel>

		<InlineFormControlLabel v-if="targetSource === 'constant'" :label="__('Value')">
			<NumberInput
				:model-value="target?.value"
				@update:model-value="setTargetValue($event)"
			/>
		</InlineFormControlLabel>

		<InlineFormControlLabel v-if="targetSource === 'measure'" :label="__('Measure')">
			<MeasurePicker
				v-model="targetMeasure"
				:column-options="columnOptions"
				@remove="target = undefined"
				@dialog-open="emit('dialog-open')"
			/>
		</InlineFormControlLabel>

		<template v-if="target">
			<InlineFormControlLabel :label="__('Gap')">
				<FormControl
					type="select"
					:options="gapOptions"
					:modelValue="target.gap || 'none'"
					@update:modelValue="setGap($event)"
				/>
			</InlineFormControlLabel>

			<InlineFormControlLabel v-if="target.gap" :label="__('Caption')">
				<FormControl
					autocomplete="off"
					:placeholder="__('vs target')"
					:modelValue="target.label"
					@update:modelValue="target = { ...target, label: $event || undefined }"
				/>
			</InlineFormControlLabel>
		</template>

		<template v-if="canDrawProgress(target, measure)">
			<Toggle :label="__('Progress bar')" v-model="progress" />

			<InlineFormControlLabel v-if="progress" :label="__('Bar color')">
				<ColorInput v-model="progressColor" placement="left-start" />
			</InlineFormControlLabel>
		</template>
	</section>

	<section class="mt-1 flex flex-col gap-2 border-t pt-3">
		<p class="text-xs-medium text-ink-gray-8">{{ __('Comparison') }}</p>

		<InlineFormControlLabel :label="__('Compare with')">
			<FormControl
				type="select"
				:options="comparisonSourceOptions"
				:modelValue="comparisonSource"
				@update:modelValue="setComparisonSource($event)"
			/>
		</InlineFormControlLabel>

		<template v-if="comparison">
			<InlineFormControlLabel :label="__('Show')">
				<TabButtons
					:options="showOptions"
					:modelValue="comparison.show || 'change'"
					@update:modelValue="comparison.show = $event"
				/>
			</InlineFormControlLabel>

			<InlineFormControlLabel :label="__('Caption')">
				<FormControl
					autocomplete="off"
					:placeholder="captionPlaceholder"
					:modelValue="comparison.label"
					@update:modelValue="comparison.label = $event || undefined"
				/>
			</InlineFormControlLabel>
		</template>

		<Toggle :label="__('Negative is better')" v-model="negativeIsBetter" />
	</section>
</template>
