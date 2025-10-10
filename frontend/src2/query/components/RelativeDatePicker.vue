<script setup lang="ts">
import { computed, reactive, watchEffect } from 'vue'
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

function parseRelativeDate(dateString: string) {
	const includeCurrentMatch = dateString.match(/\(include current\)$/)
	const cleanValue = dateString.replace(/\s*\(include current\)$/, '')
	let [span, interval, intervalType] = cleanValue.split(' ')

	if (span === 'Current') {
		intervalType = interval
		interval = '1'
	}

	return {
		span,
		interval,
		intervalType,
		includeCurrent: !!includeCurrentMatch
	}
}

function formatRelativeDate(dateParts: RelativeDateParts) {
	const baseValue = dateParts.span === 'Current'
		? `${dateParts.span} ${dateParts.intervalType}`
		: `${dateParts.span} ${dateParts.interval} ${dateParts.intervalType}`

	if (dateParts.includeCurrent && dateParts.span !== 'Current') {
		return `${baseValue} (include current)`
	}

	return baseValue
}

function getCheckboxLabel(span: string, intervalType: string) {
	if (span === 'Current') {
		return `${intervalType} to Date`
	}
	if (span === 'Last' || span === 'Next') {
		return `Include Current ${intervalType}`
	}
	return ''
}

if (relativeDate.value) {
	Object.assign(parts, parseRelativeDate(relativeDate.value))
}

watchEffect(() => {
	relativeDate.value = formatRelativeDate(parts)
})

const checkboxLabel = computed(() =>
	getCheckboxLabel(parts.span, parts.intervalType)
)
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
				{{ checkboxLabel }}
			</span>
		</div>
	</div>
</template>
