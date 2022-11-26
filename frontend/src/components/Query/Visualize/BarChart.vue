<script setup>
import Chart from '@/components/Charts/Chart.vue'
import ChartGrid from '@/components/Charts/ChartGrid.vue'
import ChartAxis from '@/components/Charts/ChartAxis.vue'
import ChartSeries from '@/components/Charts/ChartSeries.vue'
import ChartLegend from '@/components/Charts/ChartLegend.vue'
import ChartTooltip from '@/components/Charts/ChartTooltip.vue'
import { ref } from 'vue'

const props = defineProps({
	title: {
		type: String,
		default: '',
	},
	data: {
		type: Object,
		default: {},
	},
	options: {
		type: Object,
		default: {},
	},
})
const XandY = ref([
	{
		axisType: props.options.invertAxis ? 'yAxis' : 'xAxis',
		type: 'category',
		data: props.options.invertAxis ? props.data.labels.reverse() : props.data.labels,
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

const markLine = props.options.referenceLine?.value
	? {
			data: [
				{
					name: props.options.referenceLine?.label,
					type: props.options.referenceLine?.value,
					label: { position: 'middle', formatter: '{b}: {c}' },
				},
			],
	  }
	: {}
const series = ref(
	props.data.datasets.map((dataset) => ({
		type: 'bar',
		name: dataset.label,
		data: props.options.invertAxis ? dataset.data.reverse() : dataset.data,
		'itemStyle-borderRadius': '[4, 4, 0, 0]',
		markLine: markLine,
		stack: props.options.stack ? 'stack' : null,
	}))
)
</script>

<template>
	<Chart
		ref="eChart"
		:title="props.title"
		:subtitle="props.subtitle"
		:color="props.options.colors"
	>
		<ChartGrid>
			<ChartLegend type="scroll" bottom="bottom" />
			<ChartAxis v-for="(axis, i) in XandY" v-bind="axis" :key="i" />
			<ChartSeries v-for="(data, i) in series" v-bind="data" :key="i" />
			<ChartTooltip trigger="item" :appendToBody="true" />
		</ChartGrid>
	</Chart>
</template>
