<script setup>
import BaseChart from '@/components/Charts/BaseChart.vue'
import { computed, inject } from 'vue'

const $utils = inject('$utils')
const props = defineProps({
	data: { type: Object, required: true },
	options: { type: Object, required: true },
})

const dateValues = computed(() => {
	if (!props.data?.length) return
	if (!props.options.dateColumn) return
	const dateValues = props.data.map((row) => row[props.options.dateColumn])
	return dateValues
})

const values = computed(() => {
	if (!props.data?.length) return
	if (!props.options.valueColumn) return
	const values = props.data.map((row) => row[props.options.valueColumn])
	return values
})

const currentValue = computed(() => {
	if (!values.value?.length) return
	return values.value[values.value.length - 1]
})
const previousValue = computed(() => {
	if (!values.value?.length) return
	return values.value[values.value.length - 2]
})
const delta = computed(() => {
	if (!currentValue.value || !previousValue.value) return
	return currentValue.value - previousValue.value
})
const percentDelta = computed(() => {
	if (!currentValue.value || !previousValue.value) return
	return (delta.value / previousValue.value) * 100
})

const formatNumber = (val, decimals = 0) => {
	if (!props.options.hasOwnProperty('shorten') || props.options.shorten) {
		return $utils.getShortNumber(val, decimals)
	}
	return $utils.formatNumber(val, decimals)
}

const trendLineOptions = computed(() => {
	return {
		animation: false,
		grid: {
			top: 0,
			left: 0,
			right: 0,
			bottom: 0,
		},
		xAxis: {
			show: false,
			type: 'category',
			data: dateValues.value,
			boundaryGap: false,
			splitLine: false,
			axisLabel: false,
		},
		yAxis: {
			show: false,
			type: 'value',
			splitLine: false,
			axisLabel: false,
		},
		series: [
			{
				data: values.value,
				type: 'line',
				showSymbol: false,
				areaStyle: {
					opacity: 0.1,
				},
			},
		],
	}
})
</script>

<template>
	<div
		v-if="values"
		class="flex h-full w-full items-center justify-center overflow-hidden py-4 px-6"
	>
		<div
			class="mx-auto flex w-full min-w-40 max-w-[20rem] flex-col overflow-y-auto"
			:class="options.showTrendLine ? 'h-[10rem]' : 'h-fit'"
		>
			<div class="flex w-full justify-between space-x-4">
				<div
					class="overflow-hidden text-ellipsis whitespace-nowrap font-medium leading-6 text-gray-600"
				>
					{{ options.title }}
				</div>
				<Badge
					:theme="delta > 0 ? 'green' : 'red'"
					:label="
						delta > 0
							? `+${formatNumber(percentDelta, 2)}%`
							: `${formatNumber(percentDelta, 2)}%`
					"
					size="md"
				/>
			</div>
			<div class="flex items-baseline space-x-2">
				<div
					class="flex-shrink-0 overflow-hidden text-ellipsis whitespace-nowrap text-[28px] font-medium leading-10"
				>
					{{ options.prefix }}{{ formatNumber(currentValue, 2) }}{{ options.suffix }}
				</div>
				<div
					class="flex-shrink-0 overflow-hidden text-ellipsis whitespace-nowrap text-[14px] text-sm leading-5 text-gray-600"
				>
					from {{ options.prefix }}{{ formatNumber(previousValue, 2) }}{{ options.suffix }}
				</div>
			</div>
			<BaseChart v-if="options.showTrendLine" class="!px-0" :options="trendLineOptions" />
		</div>
	</div>
</template>
