<script setup lang="ts">
import { computed } from 'vue'
import InlineFormControlLabel from '../../components/InlineFormControlLabel.vue'
import { __ } from '../../translation'
import type { NumberChartConfig } from '../../types/chart.types'
import {
	NO_WINDOW,
	buildWindowSpan,
	parseWindowSpan,
	spanOfChoice,
	windowChoiceOf,
	windowChoices,
	windowUnitLabel,
} from '../window'

// The period the whole card reads. It sits on the chart, not on a value: a card
// whose values disagree about the window is two cards.

const props = defineProps<{ hasDateColumn: boolean }>()
const period = defineModel<NumberChartConfig['window']>()

const span = computed(() => parseWindowSpan(period.value?.span))
const choice = computed(() => windowChoiceOf(period.value?.span))

const choices = computed(() => {
	const options = windowChoices()
	// A span nobody here wrote — hand-authored, or written by a later release —
	// stands as its own choice, so opening the form does not drop it.
	if (options.some((option) => option.value === choice.value)) return options
	return [...options, { label: choice.value, value: choice.value }]
})

function setChoice(value: string) {
	const next = spanOfChoice(value, period.value?.span)
	period.value = next ? { ...period.value, span: next } : undefined
}

function setCount(count: any) {
	if (!span.value) return
	period.value = {
		...period.value,
		span: buildWindowSpan({ ...span.value, count: Number(count) || 1 }),
	}
}

function setIncludeCurrent(includeCurrent: boolean) {
	if (!span.value) return
	period.value = {
		...period.value,
		span: buildWindowSpan({ ...span.value, includeCurrent }),
	}
}
</script>

<template>
	<div class="flex flex-col gap-2">
		<InlineFormControlLabel label="Window">
			<p v-if="!props.hasDateColumn" class="text-xs leading-7 text-ink-gray-4">
				{{ __('Pick a date column first') }}
			</p>
			<FormControl
				v-else
				type="select"
				:options="choices"
				:modelValue="choice"
				@update:modelValue="setChoice($event)"
			/>
		</InlineFormControlLabel>

		<template v-if="props.hasDateColumn && span?.shape === 'last'">
			<div class="pl-[30%]">
				<FormControl
					type="number"
					autocomplete="off"
					placeholder="3"
					:min="1"
					:modelValue="span.count"
					@update:modelValue="setCount($event)"
				/>
			</div>

			<div class="pl-[30%]">
				<Toggle
					:label="__('Include the current {0}', windowUnitLabel(span.unit))"
					:modelValue="Boolean(span.includeCurrent)"
					@update:modelValue="setIncludeCurrent($event)"
				/>
			</div>
		</template>
	</div>
</template>
