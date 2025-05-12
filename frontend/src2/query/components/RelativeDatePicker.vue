<script setup lang="ts">
import { computed, reactive, watchEffect } from 'vue'
import Checkbox from '../../components/Checkbox.vue'

const relativeDate = defineModel<string>({
	default: () => 'Last 1 Day',
	required: true,
})

const parts = reactive({
	span: 'Last',
	interval: '1',
	intervalType: 'Day',
})

if (relativeDate.value) {
	let [span, interval, intervalType] = relativeDate.value.split(' ')

	if (span == 'Current') {
		intervalType = interval
		interval = '1'
	}

	parts.span = span
	parts.interval = interval
	parts.intervalType = intervalType
}

watchEffect(() => {
	relativeDate.value =
		parts.span == 'Current'
			? `${parts.span} ${parts.intervalType}`
			: `${parts.span} ${parts.interval} ${parts.intervalType}`
})

const checkboxLabel = computed(() => {
	if (parts.span == 'Current') {
		return parts.intervalType + ' to Date'
	}
	if (parts.span == 'Last') {
		return 'Include Current ' + parts.intervalType
	}
	if (parts.span == 'Next') {
		return 'Include Current ' + parts.intervalType
	}
})
</script>

<template>
	<div class="flex w-[15rem] select-none flex-col gap-2 rounded bg-white text-base">
		<div class="flex gap-2">
			<FormControl
				type="select"
				v-model="parts.span"
				class="flex-[3] flex-shrink-0 text-sm"
				:options="['Last', 'Current', 'Next']"
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
				:options="['Day', 'Week', 'Month', 'Quarter', 'Year', 'Fiscal Year']"
			/>
		</div>
		<div v-if="false" class="flex items-center gap-2">
			<Toggle size="sm" />
			<span class="text-p-sm text-gray-600">{{ checkboxLabel }}</span>
		</div>
	</div>
</template>
