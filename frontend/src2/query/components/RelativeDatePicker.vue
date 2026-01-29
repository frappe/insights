<script setup lang="ts">
import { reactive, watchEffect } from 'vue'
import { FormControl } from 'frappe-ui'
import { RelativeDateParts, SPAN_OPTIONS, INTERVAL_TYPE_OPTIONS } from '../../types/query.types'

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

if (relativeDate.value) {
	const includeCurrent = /\(include current\)$/.test(relativeDate.value)
	const clean = relativeDate.value.replace(/\s*\(include current\)$/, '')
	const tokens = clean.split(' ')
	parts.span = tokens[0]
	if (parts.span === 'Current') {
		parts.interval = '1'
		parts.intervalType = tokens.slice(1).join(' ')
	} else {
		parts.interval = tokens[1]
		parts.intervalType = tokens.slice(2).join(' ')
	}
	parts.includeCurrent = includeCurrent
}

watchEffect(() => {
	if (parts.intervalType === 'Fiscal Year') parts.includeCurrent = false
	const base = parts.span === 'Current'
		? `${parts.span} ${parts.intervalType}`
		: `${parts.span} ${parts.interval} ${parts.intervalType}`
	relativeDate.value = parts.includeCurrent && parts.span !== 'Current'
		? `${base} (include current)`
		: base
})

const toggleLabel = (span: string, intervalType: string) =>
	span === 'Current' ? `${intervalType} to Date` : `Include Current ${intervalType}`
</script>

<template>
	<div class="flex w-[15rem] select-none flex-col gap-2 rounded bg-white text-base">
		<div class="flex gap-2">
			<FormControl
				type="select"
				v-model="parts.span"
				class="flex-[3] flex-shrink-0 text-sm"
				:options="SPAN_OPTIONS"
			/>
			<FormControl
				v-if="parts.span !== 'Current'"
				type="number"
				v-model="parts.interval"
				class="flex-[2] flex-shrink-0 text-sm"
			/>
			<FormControl
				type="select"
				v-model="parts.intervalType"
				class="flex-[3] flex-shrink-0 text-sm"
				:options="INTERVAL_TYPE_OPTIONS"
			/>
		</div>
		<div v-if="parts.span !== 'Current' && parts.intervalType !== 'Fiscal Year'" class="flex items-center gap-2">
			<Toggle size="sm" v-model="parts.includeCurrent" />
			<span class="text-p-sm text-gray-600">
				{{ toggleLabel(parts.span, parts.intervalType) }}
			</span>
		</div>
	</div>
</template>
