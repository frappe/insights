<script setup lang="ts">
import { formatNumber, getShortNumber } from '@/utils'
import { computed } from 'vue'
import { Chart } from '../chart'
import { MetricChartConfig } from '../helpers'

const props = defineProps<{ chart: Chart }>()

const config = computed(() => props.chart.doc.config as MetricChartConfig)
const formattedValue = computed(() => {
	if (!config.value.metric_column || !props.chart.dataQuery.result.rows) {
		return null
	}

	const rows = props.chart.dataQuery.result.rows
	const metric_values = rows.map((row) => row[config.value.metric_column])
	const _value = metric_values.reduce((a, b) => a + b, 0)

	if (config.value.shorten_numbers) {
		return getShortNumber(_value, config.value.precision)
	}
	return formatNumber(_value, config.value.precision)
})
</script>

<template>
	<div
		v-if="formattedValue"
		class="flex h-full w-full items-center justify-center overflow-hidden px-8 py-4"
	>
		<div
			class="mx-auto flex h-full max-h-[10rem] w-full min-w-40 max-w-[20rem] flex-col justify-center overflow-y-auto"
		>
			<div class="w-full">
				<span class="truncate font-medium leading-6">{{ config.metric_column }}</span>
			</div>
			<div class="text-[28px] font-medium leading-10">
				{{ config.prefix }}{{ formattedValue }}{{ config.suffix }}
			</div>
		</div>
	</div>
	<template v-else>
		<slot name="placeholder"></slot>
	</template>
</template>
