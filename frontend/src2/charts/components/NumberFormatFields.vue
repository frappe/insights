<script setup lang="ts">
import { computed } from 'vue'
import InlineFormControlLabel from '../../components/InlineFormControlLabel.vue'
import type { NumberFormat, NumberFormatConfig } from '../../types/chart.types'

// The one form behind the one policy: how a chart's numbers print. Named a
// Measure, it writes that Measure's own format. Named none, it writes the
// chart's default, which every value of the chart inherits.
//
// It writes `number_format` and `number_formats` alone. `shorten_numbers`,
// `compact_numbers` and `decimal` are still read — a chart nobody opens keeps
// printing as it did — but nothing writes them again.
const props = defineProps<{
	config: NumberFormatConfig
	/** The Measure this states the format of. Left out, the chart's default. */
	measureName?: string
}>()

const format = computed<NumberFormat>(() => {
	if (!props.measureName) return props.config.number_format || {}
	return props.config.number_formats?.[props.measureName] || {}
})

function write(key: keyof NumberFormat, value: any) {
	const written: NumberFormat = { ...format.value }
	// An empty prefix is a prefix of nothing, which is an answer. An empty
	// decimals is no answer, so the key goes rather than reading as zero.
	if (value === undefined) delete written[key]
	else (written as any)[key] = value

	if (!props.measureName) {
		props.config.number_format = written
		return
	}
	props.config.number_formats = {
		...(props.config.number_formats || {}),
		[props.measureName]: written,
	}
}

function writeDecimals(value: any) {
	write('decimals', value === '' || value === null ? undefined : Number(value))
}
</script>

<template>
	<InlineFormControlLabel label="Units">
		<div class="grid grid-cols-3 gap-1">
			<FormControl
				autocomplete="off"
				placeholder="$"
				:modelValue="format.prefix"
				@update:modelValue="write('prefix', $event)"
			/>
			<FormControl
				autocomplete="off"
				placeholder="unit"
				:modelValue="format.suffix"
				@update:modelValue="write('suffix', $event)"
			/>
			<FormControl
				autocomplete="off"
				placeholder="0.0"
				type="number"
				:modelValue="format.decimals"
				@update:modelValue="writeDecimals($event)"
			/>
		</div>
	</InlineFormControlLabel>
	<Toggle
		label="Show short numbers"
		:modelValue="format.shorten"
		@update:modelValue="write('shorten', $event)"
	/>
</template>
