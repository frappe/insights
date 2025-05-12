<script setup lang="ts">
import { graphic } from 'echarts/core'
import { getColors } from '../colors'
import BaseChart from './BaseChart.vue'
import { computed } from 'vue'

const props = defineProps<{ dates: string[]; values: number[]; color?: string }>()

const color = computed(() => props.color || getColors()[0])
const gradient = computed(() => {
	return new graphic.LinearGradient(0, 0, 0, 1, [
		{ offset: 0, color: color.value },
		{ offset: 1, color: '#fff' },
	])
})
</script>

<template>
	<BaseChart
		:options="{
			animation: true,
			animationDuration: 700,
			grid: {
				top: '20%',
				left: 0,
				right: 0,
				bottom: 0,
			},
			xAxis: {
				show: false,
				type: 'category',
				data: props.dates,
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
					data: props.values,
					type: 'line',
					showSymbol: false,
					color: color,
					areaStyle: {
						color: gradient,
						opacity: 0.3,
					},
				},
			],
		}"
	/>
</template>
