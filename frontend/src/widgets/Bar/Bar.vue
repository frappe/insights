<script setup>
import Chart from '@/components/Charts/Chart.vue'
import ChartAxis from '@/components/Charts/ChartAxis.vue'
import ChartGrid from '@/components/Charts/ChartGrid.vue'
import ChartLegend from '@/components/Charts/ChartLegend.vue'
import ChartSeries from '@/components/Charts/ChartSeries.vue'
import ChartTooltip from '@/components/Charts/ChartTooltip.vue'
import { computed } from 'vue'

const props = defineProps({
	chartData: { type: Object, required: true },
	options: { type: Object, required: true },
})

const results = computed(() => props.chartData.data)
const labels = computed(() => {
	if (!results.value?.length || !props.options.xAxis) return []
	const columns = results.value[0].map((d) => d.label)
	const columnIndex = columns.indexOf(props.options.xAxis)
	return results.value.slice(1).map((d) => d[columnIndex])
})

const datasets = computed(() => {
	if (!results.value?.length || !props.options.yAxis) return []
	return props.options.yAxis.map((column) => {
		const columns = results.value[0].map((d) => d.label)
		const columnIndex = columns.indexOf(column)
		return {
			label: column,
			data: results.value.slice(1).map((d) => d[columnIndex]),
		}
	})
})

const XandY = computed(() => [
	{
		axisType: props.options.invertAxis ? 'yAxis' : 'xAxis',
		type: 'category',
		data: props.options.invertAxis ? labels.value.reverse() : labels.value,
		axisTick: false,
		'axisLabel-interval': 0,
		'axisLabel-rotate': props.options.rotateLabels,
	},
	{
		axisType: props.options.invertAxis ? 'xAxis' : 'yAxis',
		type: 'value',
		'splitLine-lineStyle-type': 'dashed',
	},
])

const markLine = computed(() =>
	props.options.referenceLine
		? {
				data: [
					{
						name: props.options.referenceLine,
						type: props.options.referenceLine.toLowerCase(),
						label: { position: 'middle', formatter: '{b}: {c}' },
					},
				],
		  }
		: {}
)

const series = computed(() =>
	datasets.value.map((dataset) => ({
		type: 'bar',
		name: dataset.label,
		barMaxWidth: 50,
		data: props.options.invertAxis ? dataset.data.reverse() : dataset.data,
		'itemStyle-borderRadius': '[4, 4, 0, 0]',
		markLine: markLine,
		stack: props.options.stack ? 'stack' : null,
		itemStyle: {
			normal: {
				barBorderRadius: props.options.invertAxis ? [0, 4, 4, 0] : [4, 4, 0, 0],
			},
		},
	}))
)

function valueFormatter(value) {
	return isNaN(value) ? value : value.toLocaleString()
}

const shouldRender = computed(() => {
	return !!labels.value.length && !!datasets.value.length
})
</script>

<template>
	<Chart
		v-if="shouldRender"
		ref="eChart"
		:chartTitle="props.options.title"
		:chartSubtitle="props.options.subtitle"
		:color="props.options.colors"
	>
		<ChartGrid>
			<ChartLegend type="scroll" bottom="bottom" />
			<ChartAxis v-for="(axis, i) in XandY" v-bind="axis" :key="i" />
			<ChartSeries v-for="(data, i) in series" v-bind="data" :key="i" />
			<ChartTooltip trigger="axis" :appendToBody="true" :valueFormatter="valueFormatter" />
		</ChartGrid>
	</Chart>
	<div v-else>
		<slot name="placeholder"></slot>
	</div>
</template>
