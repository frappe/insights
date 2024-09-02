<script setup lang="ts">
import { computed } from 'vue'
import { formatNumber, getShortNumber } from '../../helpers'
import { NumberChartConfig } from '../../types/chart.types'
import { Measure } from '../../types/query.types'
import { Chart } from '../chart'
import Sparkline from './Sparkline.vue'

const props = defineProps<{ chart: Chart }>()

const title = computed(() => props.chart.doc.title)
const config = computed(() => props.chart.doc.config as NumberChartConfig)

const dateValues = computed(() => {
	if (!config.value.date_column) return []
	const date_column = config.value.date_column.column_name
	return props.chart.dataQuery.result.rows.map((row: any) => row[date_column])
})
const numberValuesPerColumn = computed(() => {
	if (!config.value.number_columns?.length) return {}
	if (!props.chart.dataQuery.result?.rows) return {}

	return config.value.number_columns
		.map((c) => c.measure_name)
		.reduce((acc: any, column: string) => {
			acc[column] = props.chart.dataQuery.result.rows.map((row: any) => row[column])
			return acc
		}, {})
})

const cards = computed(() => {
	if (!config.value.number_columns?.length) return []
	if (!props.chart.dataQuery.result?.rows) return []

	return config.value.number_columns.map((column: Measure) => {
		const numberValues = numberValuesPerColumn.value[column.measure_name]
		const currentValue = numberValues[numberValues.length - 1]
		const previousValue = numberValues[numberValues.length - 2]
		const delta = config.value.negative_is_better
			? previousValue - currentValue
			: currentValue - previousValue
		const percentDelta = (delta / previousValue) * 100
		return {
			column,
			currentValue: getFormattedValue(currentValue),
			previousValue: getFormattedValue(previousValue),
			delta,
			percentDelta: getFormattedValue(percentDelta),
		}
	})
})

const getFormattedValue = (value: number) => {
	if (isNaN(value)) return 0
	if (config.value.shorten_numbers) {
		return getShortNumber(value, config.value.decimal)
	}
	return formatNumber(value, config.value.decimal)
}
</script>

<template>
	<div class="grid w-full grid-cols-[repeat(auto-fill,214px)] gap-4">
		<div
			v-for="{ column, currentValue, delta, percentDelta } in cards"
			:key="column.measure_name"
			class="flex h-[140px] items-center gap-2 overflow-y-auto rounded bg-white py-4 px-6 shadow"
		>
			<div class="flex w-full flex-col">
				<span class="truncate text-sm font-medium">
					{{ column.measure_name }}
				</span>
				<div class="flex-1 flex-shrink-0 text-[24px] font-semibold leading-10">
					{{ config.prefix }}{{ currentValue }}{{ config.suffix }}
				</div>
				<div
					v-if="config.comparison"
					class="flex items-center gap-1 text-xs font-medium"
					:class="delta >= 0 ? 'text-green-500' : 'text-red-500'"
				>
					<span class="">
						{{ delta >= 0 && !config.negative_is_better ? '↑' : '↓' }}
					</span>
					<span> {{ percentDelta }}% </span>
				</div>
				<div v-if="config.sparkline" class="mt-2 h-[18px] w-[80px]">
					<Sparkline
						:dates="dateValues"
						:values="numberValuesPerColumn[column.measure_name]"
					/>
				</div>
			</div>
		</div>
	</div>
</template>
