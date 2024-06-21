<script setup lang="ts">
import { formatNumber, getShortNumber } from '@/utils'
import { computed } from 'vue'
import { NumberChartConfig } from '../../types/chart.types'
import { Chart } from '../chart'
import Sparkline from './Sparkline.vue'

const props = defineProps<{ chart: Chart }>()

const title = computed(() => props.chart.doc.title)
const config = computed(() => props.chart.doc.config as NumberChartConfig)
const formattedValue = computed(() => {
	if (!config.value.number_column || !props.chart.dataQuery.result.rows) {
		return null
	}

	const rows = props.chart.dataQuery.result.rows
	const number_values = rows.map((row: any) => row[config.value.number_column])
	const _value = number_values.reduce((a: number, b: number) => a + b, 0)

	if (config.value.shorten_numbers) {
		return getShortNumber(_value, config.value.precision)
	}
	return formatNumber(_value, config.value.precision)
})

const dateValues = computed(() => {
	if (!config.value.date_column) return []
	const date_column = config.value.date_column
	return props.chart.dataQuery.result.rows.map((row: any) => row[date_column])
})
const numberValues = computed(() => {
	if (!config.value.number_column) return []
	return props.chart.dataQuery.result.rows.map((row: any) => row[config.value.number_column])
})

const currentValue = computed(() => {
	if (!numberValues.value?.length) return
	return numberValues.value[numberValues.value.length - 1]
})
const previousValue = computed(() => {
	if (!numberValues.value?.length) return
	return numberValues.value[numberValues.value.length - 2]
})
const delta = computed(() => {
	if (currentValue.value === undefined || previousValue.value === undefined) return 0
	return config.value.negative_is_better
		? previousValue.value - currentValue.value
		: currentValue.value - previousValue.value
})
const percentDelta = computed(() => {
	if (currentValue.value === undefined || previousValue.value === undefined) {
		return 0
	}
	return (delta.value / previousValue.value) * 100
})
</script>

<template>
	<div
		v-if="formattedValue"
		class="flex h-full w-full items-center justify-center overflow-hidden p-6"
	>
		<div
			class="mx-auto flex h-full max-h-[10rem] w-full min-w-[10rem] max-w-[16rem] items-center gap-2 overflow-y-auto"
		>
			<div class="flex w-full flex-col">
				<div class="w-full">
					<span class="truncate font-medium leading-6">
						{{ title || config.number_column }}
					</span>
				</div>
				<div class="mb-1 flex items-center justify-between gap-4">
					<div class="flex-shrink-0 text-[28px] font-medium leading-10">
						{{ config.prefix }}{{ formattedValue }}{{ config.suffix }}
					</div>
					<div class="h-[40px] max-w-[8rem] flex-1">
						<Sparkline
							v-if="config.sparkline"
							:dates="dateValues"
							:values="numberValues"
						/>
					</div>
				</div>
				<div
					v-if="config.comparison"
					class="flex text-sm"
					:class="delta >= 0 ? 'text-green-500' : 'text-red-500'"
				>
					<span class="">
						{{ delta >= 0 ? '+' : '-' }}
					</span>
					<span class="tnum"> {{ formatNumber(Math.abs(percentDelta), 2) }}% </span>
				</div>
			</div>
		</div>
	</div>
</template>
