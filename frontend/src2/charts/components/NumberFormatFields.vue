<script setup lang="ts">
import { computed } from 'vue'
import InlineFormControlLabel from '../../components/InlineFormControlLabel.vue'
import InputGroup, { type InputGroupField } from '../../components/InputGroup.vue'
import type { NumberFormat, NumberFormatConfig } from '../../types/chart.types'
import { inheritedNumberFormat } from '../number_format'

// The one form behind the one policy: how a chart's numbers print. Named a
// Measure, it writes that Measure's own format. Named none, it writes the
// chart's default, which every value of the chart inherits.
//
// It writes `number_format` and `number_formats` alone. `shorten_numbers`,
// `compact_numbers` and `decimal` are still read — a chart nobody opens keeps
// printing as it did — but nothing writes them again.
//
// Prefix, suffix and precision are one control, not three, because they are
// three readings of one question. `InputGroup` frames them the way Builder
// frames the sides of a margin: one frame, a name under each field, and a
// placeholder that states what the field inherits.
const props = defineProps<{
	config: NumberFormatConfig
	/** The Measure this states the format of. Left out, the chart's default. */
	measureName?: string
	/**
	 * The one Measure a single-Measure chart draws. It has no per-Measure
	 * override, because the override and the default would say the same thing
	 * and the override would win silently. An earlier release wrote that
	 * chart's format under the Measure, so the default reads it while it is the
	 * only answer, and the first write lifts it into `number_format` and drops
	 * the entry. Nothing reads it twice.
	 */
	soleMeasureName?: string
}>()

const format = computed<NumberFormat>(() => {
	if (props.measureName) return props.config.number_formats?.[props.measureName] || {}

	const chartDefault = props.config.number_format
	if (chartDefault && Object.keys(chartDefault).length) return chartDefault
	if (props.soleMeasureName) {
		return props.config.number_formats?.[props.soleMeasureName] || {}
	}
	return chartDefault || {}
})

/** What a key left unstated prints as. The fields show it as their placeholder. */
const inherited = computed(() => inheritedNumberFormat(props.config, props.measureName))

function write(key: keyof NumberFormat, value: any) {
	const written: NumberFormat = { ...format.value }
	// An empty prefix is a prefix of nothing, which is an answer. `undefined` is
	// no answer, so the key goes and the layer under this one prints again.
	if (value === undefined) delete written[key]
	else (written as any)[key] = value

	if (props.measureName) {
		props.config.number_formats = {
			...(props.config.number_formats || {}),
			[props.measureName]: written,
		}
		return
	}

	props.config.number_format = written
	if (props.soleMeasureName && props.config.number_formats?.[props.soleMeasureName]) {
		const rest = { ...props.config.number_formats }
		delete rest[props.soleMeasureName]
		props.config.number_formats = rest
	}
}

// A negative precision is not a precision, and the resolver clamps one away.
// The field refuses to hold one so what is stored says what is drawn.
function writeDecimals(value: any) {
	const decimals = Number(value)
	if (value === '' || value === null || value === undefined || isNaN(decimals)) {
		write('decimals', undefined)
		return
	}
	write('decimals', Math.max(0, Math.floor(decimals)))
}

function writeField(key: string, value: string) {
	if (key === 'decimals') return writeDecimals(value)
	write(key as keyof NumberFormat, value)
}

// A placeholder answers one of two questions, in this order: what does this
// field inherit, and failing that, what does an answer look like. An example
// carries more than the word "none", which states an absence the empty field
// already states.
const EXAMPLES = { prefix: '$', suffix: '%', decimals: '2' }

const fields = computed<InputGroupField[]>(() => [
	{
		key: 'prefix',
		label: 'Prefix',
		value: format.value.prefix,
		placeholder: inherited.value.prefix || EXAMPLES.prefix,
	},
	{
		key: 'suffix',
		label: 'Suffix',
		value: format.value.suffix,
		placeholder: inherited.value.suffix || EXAMPLES.suffix,
	},
	{
		key: 'decimals',
		label: 'Decimals',
		value: format.value.decimals,
		// Unstated, the locale picks the places from the number itself, so no
		// one number stands for what it inherits.
		placeholder:
			inherited.value.decimals === undefined
				? EXAMPLES.decimals
				: String(inherited.value.decimals),
		type: 'number',
		min: 0,
		max: 20,
	},
])
</script>

<template>
	<!-- No field here holds more than a few characters, but three of them and
	     their names need the room. -->
	<InlineFormControlLabel label="Format" control-width="10rem">
		<InputGroup :fields="fields" @update="writeField" />
	</InlineFormControlLabel>

	<Toggle
		label="Short numbers"
		:modelValue="format.shorten"
		@update:modelValue="write('shorten', $event)"
	/>
</template>
