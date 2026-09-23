<script setup lang="ts">
import { FormControl } from 'frappe-ui'
import { reactive, watch } from 'vue'
import { parseSpan, type SpanShape } from '../../helpers/span_grammar'
import { INTERVAL_TYPE_OPTIONS, RelativeDateParts, SPAN_OPTIONS } from '../../types/query.types'

const relativeDate = defineModel<string>({
	default: () => 'Last 1 Day',
	required: true,
})

const parts = reactive<RelativeDateParts>({
	span: 'Last',
	interval: '1',
	intervalType: 'Day',
	includeCurrent: false,
})

// A count of nothing is not a window: a number box the reader cleared writes one
// interval rather than a string the server cannot read.
function toCount(token?: string) {
	const count = parseInt(token || '')
	return count > 0 ? String(count) : '1'
}

// The three controls are one span, in the words the options are written in. The
// grammar itself is `span_grammar`, which the server reads the same way, so a
// span stored in any of its forms opens on the window it names — including the
// countless "Last Month", which covers one period.
//
// Three of the grammar's four shapes. `<unit> to date` — the period so far — has
// no option in `SPAN_OPTIONS` to draw it with, and a span this picker cannot
// read is one it must not write over: Copy JSON, an import and a hand-authored
// workbook all put spans in this field that the picker never offered.
const SPAN_WORD: Partial<Record<SpanShape, string>> = {
	last: 'Last',
	current: 'Current',
	next: 'Next',
}

const stored = parseSpan(relativeDate.value)
const storedSpan = stored && SPAN_WORD[stored.shape]
if (stored && storedSpan) {
	parts.span = storedSpan
	parts.interval = String(stored.count)
	parts.intervalType = stored.unit.replace(/\b\w/g, (letter) => letter.toUpperCase())
	parts.includeCurrent = stored.includeCurrent
}

/** The span the three controls say, as the server reads it. */
function written() {
	if (parts.intervalType === 'Fiscal Year') parts.includeCurrent = false
	const base =
		parts.span === 'Current'
			? `${parts.span} ${parts.intervalType}`
			: `${parts.span} ${toCount(parts.interval)} ${parts.intervalType}`
	return parts.includeCurrent && parts.span !== 'Current' ? `${base} (include current)` : base
}

// Opening the picker on a span it could read is already a round trip: "Last
// Month" is stored back as "Last 1 Month", the form the controls stand for.
// Opening it on anything else is not editing it, so nothing is written until a
// control moves.
if (storedSpan) relativeDate.value = written()
watch(parts, () => (relativeDate.value = written()))

const toggleLabel = (span: string, intervalType: string) =>
	span === 'Current' ? `${intervalType} to Date` : `Include Current ${intervalType}`
</script>

<template>
	<!-- The picker fills whatever box it is given: the filter editor's row and the
	     filter popover both hand it one, and a width of its own overflowed them. -->
	<div class="flex w-full min-w-0 select-none flex-col gap-2 text-base">
		<div class="flex w-full min-w-0 flex-wrap gap-2">
			<FormControl
				type="select"
				v-model="parts.span"
				class="min-w-[6rem] flex-1"
				:options="SPAN_OPTIONS"
			/>
			<FormControl
				v-if="parts.span !== 'Current'"
				type="number"
				v-model="parts.interval"
				class="w-14 flex-shrink-0"
				min="1"
				placeholder="1"
			/>
			<FormControl
				type="select"
				v-model="parts.intervalType"
				class="min-w-[6rem] flex-1"
				:options="INTERVAL_TYPE_OPTIONS"
			/>
		</div>
		<!-- The switch leads its row, so it starts where the row above it does. -->
		<Toggle
			v-if="parts.span !== 'Current' && parts.intervalType !== 'Fiscal Year'"
			v-model="parts.includeCurrent"
			control-position="start"
			:label="toggleLabel(parts.span, parts.intervalType)"
		/>
	</div>
</template>

<style scoped>
/* A spinner crowds a field this narrow, and the count steps by the keyboard. */
:deep(input[type='number']::-webkit-outer-spin-button),
:deep(input[type='number']::-webkit-inner-spin-button) {
	appearance: none;
	margin: 0;
}

:deep(input[type='number']) {
	appearance: textfield;
}
</style>
