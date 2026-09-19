<script setup lang="ts">
import { FormControl } from 'frappe-ui'
import { reactive, watchEffect } from 'vue'
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

// A count of nothing is not a window, and a value authored before the count
// existed carries none. Either way the picker opens on one interval rather than
// on an empty box that emits an unparseable string.
function toCount(token?: string) {
	const count = parseInt(token || '')
	return count > 0 ? String(count) : '1'
}

if (relativeDate.value) {
	const includeCurrent = /\(include current\)$/.test(relativeDate.value)
	const clean = relativeDate.value.replace(/\s*\(include current\)$/, '')
	const tokens = clean.split(' ').filter(Boolean)
	parts.span = tokens[0]
	if (parts.span === 'Current') {
		parts.interval = '1'
		parts.intervalType = tokens.slice(1).join(' ')
	} else {
		parts.interval = toCount(tokens[1])
		parts.intervalType = tokens.slice(2).join(' ')
	}
	parts.includeCurrent = includeCurrent
}

watchEffect(() => {
	if (parts.intervalType === 'Fiscal Year') parts.includeCurrent = false
	const base =
		parts.span === 'Current'
			? `${parts.span} ${parts.intervalType}`
			: `${parts.span} ${toCount(parts.interval)} ${parts.intervalType}`
	relativeDate.value =
		parts.includeCurrent && parts.span !== 'Current' ? `${base} (include current)` : base
})

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
