<script setup lang="ts">
import { reactive, watchEffect, watch } from 'vue'
import { FormControl } from 'frappe-ui'
import { RelativeDateParts, SPAN_OPTIONS, INTERVAL_TYPE_OPTIONS } from '../../types/query.types'
import { __ } from '../../translation'
import PresetWrapper from './PresetWrapper.vue'
import { getDatePresets } from './filter_utils'

const relativeDate = defineModel<string>()

const parts = reactive<RelativeDateParts>({
	span: 'Current',
	interval: '1',
	intervalType: 'Day',
	includeCurrent: false,
})

const parseRelativeDate = (relativeDateString: string | undefined) => {
	if (!relativeDateString) return
	const includeCurrent = /\(include current\)$/.test(relativeDateString)
	const clean = relativeDateString.replace(/\s*\(include current\)$/, '')
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

watch(
	() => relativeDate.value,
	(newRelativeDate) => {
		parseRelativeDate(newRelativeDate)
	},
	{ immediate: true },
)

watchEffect(() => {
	if (parts.intervalType === 'Fiscal Year') parts.includeCurrent = false
	const base =
		parts.span === 'Current'
			? `${parts.span} ${parts.intervalType}`
			: `${parts.span} ${parts.interval} ${parts.intervalType}`
	relativeDate.value =
		parts.includeCurrent && parts.span !== 'Current' ? `${base} (include current)` : base
})

const toggleLabel = (span: string, intervalType: string) =>
	span === 'Current' ? `${intervalType} to Date` : `Include Current ${intervalType}`

const presets = getDatePresets('within')
</script>

<template>
	<div class="w-[15rem] select-none text-base flex flex-col gap-2">
		<PresetWrapper v-model="relativeDate" :presets="presets">
			<div class="flex flex-col gap-2 rounded bg-white w-full">
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
				<div
					v-if="parts.span !== 'Current' && parts.intervalType !== 'Fiscal Year'"
					class="flex items-center gap-2"
				>
					<Toggle size="sm" v-model="parts.includeCurrent" />
					<span class="text-p-sm text-gray-600">
						{{ toggleLabel(parts.span, parts.intervalType) }}
					</span>
				</div>
			</div>
		</PresetWrapper>
	</div>
</template>
