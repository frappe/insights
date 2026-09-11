<script setup lang="ts">
import { Combobox, Tooltip } from 'frappe-ui'
import { InfoIcon } from 'lucide-vue-next'
import { computed } from 'vue'
import InlineFormControlLabel from '../../components/InlineFormControlLabel.vue'
import { __ } from '../../translation'
import type { NumberChartConfig } from '../../types/chart.types'
import {
	buildWindowSpan,
	choiceOfPeriod,
	includeCurrentLabel,
	parseWindowSpan,
	periodOfChoice,
	windowChoiceGroups,
	windowUnitLabel,
	type WindowSpan,
} from '../window'

// The period the whole card reads. It sits on the chart, not on a value: a card
// whose values disagree about the window is two cards.

const props = defineProps<{ hasDateColumn: boolean }>()
const period = defineModel<NumberChartConfig['window']>()

const span = computed(() => parseWindowSpan(period.value?.span))
const choice = computed(() => choiceOfPeriod(period.value))

const choices = computed(() => {
	const groups = windowChoiceGroups()
	const known = groups.some((group) =>
		group.options.some((option) => option.value === choice.value),
	)
	// Nothing chosen yet shows the placeholder, so there is no entry to keep.
	if (!choice.value || known) return groups

	// A period nobody here wrote — hand-authored, or written by a later release —
	// stands as its own choice, so opening the form does not drop it. Under no
	// heading, because it belongs to no family.
	return [
		...groups,
		{
			group: choice.value,
			hideLabel: true,
			options: [{ label: choice.value, value: choice.value }],
		},
	]
})

function setChoice(value: unknown) {
	const next = value ? periodOfChoice(String(value), period.value) : undefined
	// The anchor is the author's, not the choice's, so it stays when the choice
	// changes.
	const anchor = period.value?.anchor
	period.value = next && anchor ? { ...next, anchor } : next
}

// Written whole, the way `setChoice` writes it: a period names one shape, and
// the anchor is the only thing that crosses from the one it replaces.
function setSpan(span: WindowSpan) {
	const anchor = period.value?.anchor
	period.value = { span: buildWindowSpan(span), ...(anchor ? { anchor } : {}) }
}

function setCount(count: any) {
	if (span.value) setSpan({ ...span.value, count: Number(count) || 1 })
}

function setIncludeCurrent(includeCurrent: boolean) {
	if (span.value) setSpan({ ...span.value, includeCurrent })
}
</script>

<template>
	<div class="flex flex-col gap-2">
		<InlineFormControlLabel label="Period">
			<template #label-suffix>
				<Tooltip>
					<InfoIcon class="h-3 w-3 text-ink-gray-4" />
					<template #content>
						<p class="max-w-56 leading-relaxed">
							{{
								__(
									'The card reads the newest period; a comparison reads an earlier one.',
								)
							}}
						</p>
					</template>
				</Tooltip>
			</template>

			<Combobox
				class="w-full"
				:disabled="!props.hasDateColumn"
				:placeholder="props.hasDateColumn ? __('Pick a period') : __('Pick a date column')"
				:options="choices"
				:modelValue="(props.hasDateColumn && choice) || null"
				@update:modelValue="setChoice($event)"
			/>
		</InlineFormControlLabel>

		<template v-if="props.hasDateColumn && span?.shape === 'last'">
			<!-- The option above says "Last N months". This is the same sentence
			     with the blank filled, so the count never stands on its own. -->
			<div class="flex items-center gap-1.5 pl-[30%]">
				<span class="text-p-sm text-ink-gray-5">{{ __('Last') }}</span>
				<FormControl
					type="number"
					autocomplete="off"
					class="w-14"
					:min="1"
					:modelValue="span.count"
					@update:modelValue="setCount($event)"
				/>
				<span class="text-p-sm text-ink-gray-5">
					{{ windowUnitLabel(span.unit, (span.count || 1) !== 1) }}
				</span>
			</div>

			<div class="pl-[30%]">
				<Toggle
					:label="includeCurrentLabel(span.unit)"
					:modelValue="Boolean(span.includeCurrent)"
					@update:modelValue="setIncludeCurrent($event)"
				/>
			</div>
		</template>
	</div>
</template>
