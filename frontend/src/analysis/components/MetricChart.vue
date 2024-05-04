<script setup lang="ts">
import { computed, inject } from 'vue'
import { AnalysisChart } from '../useAnalysisChart'
import { MetricChartConfig } from './chart_utils'
import { getShortNumber, formatNumber } from '@/utils'

const props = defineProps<{ chart: AnalysisChart }>()

const config = computed(() => props.chart.options as MetricChartConfig)
const formattedValue = computed(() => {
	const rows = props.chart.query.result.rows
	if (!rows.length) return

	if (!config.value.metric_column) return
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
			<!-- <div class="w-full">
				<span class="truncate font-medium leading-6">{{ props.options.title }}</span>
			</div> -->
			<div class="text-[28px] font-medium leading-10">
				{{ config.prefix }}{{ formattedValue }}{{ config.suffix }}
			</div>
		</div>
	</div>
	<template v-else>
		<slot name="placeholder"></slot>
	</template>
</template>
