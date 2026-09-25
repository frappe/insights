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

// A cleared or zero count writes 1. The server cannot read a span without a
// count.
function toCount(token?: string) {
	const count = parseInt(token || '')
	return count > 0 ? String(count) : '1'
}

// Maps the span shapes of `span_grammar` to the words in `SPAN_OPTIONS`. The
// server parses spans with the same grammar, so a stored span in any of its
// forms opens on the right controls. That includes "Last Month" with no count,
// which means one period.
//
// Only three of the four shapes are here. `<unit> to date` has no option in
// `SPAN_OPTIONS`. The picker must not overwrite a span it cannot read: Copy
// JSON, an import or a hand-written workbook can store spans the picker never
// listed.
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

/** The span string the three controls describe, in the server's format. */
function written() {
	if (parts.intervalType === 'Fiscal Year') parts.includeCurrent = false
	const base =
		parts.span === 'Current'
			? `${parts.span} ${parts.intervalType}`
			: `${parts.span} ${toCount(parts.interval)} ${parts.intervalType}`
	return parts.includeCurrent && parts.span !== 'Current' ? `${base} (include current)` : base
}

// A span the picker can read is written back at once in the controls' form:
// "Last Month" becomes "Last 1 Month". Any other span stays as stored until the
// user changes a control.
if (storedSpan) relativeDate.value = written()
watch(parts, () => (relativeDate.value = written()))

const toggleLabel = (span: string, intervalType: string) =>
	span === 'Current' ? `${intervalType} to Date` : `Include Current ${intervalType}`
</script>

<template>
	<!-- The picker fills the width it is given. The filter editor's row and the
	     filter popover both set that width, and a fixed width overflowed them. -->
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
		<!-- The switch comes first, so it lines up with the fields above. -->
		<Toggle
			v-if="parts.span !== 'Current' && parts.intervalType !== 'Fiscal Year'"
			v-model="parts.includeCurrent"
			control-position="start"
			:label="toggleLabel(parts.span, parts.intervalType)"
		/>
	</div>
</template>

<style scoped>
/* The spin buttons crowd a field this narrow. The arrow keys still step the count. */
:deep(input[type='number']::-webkit-outer-spin-button),
:deep(input[type='number']::-webkit-inner-spin-button) {
	appearance: none;
	margin: 0;
}

:deep(input[type='number']) {
	appearance: textfield;
}
</style>
