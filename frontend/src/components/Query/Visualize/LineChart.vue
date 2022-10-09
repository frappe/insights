<script setup>
import Chart from '@/components/Charts/Chart.vue'
import ChartGrid from '@/components/Charts/ChartGrid.vue'
import ChartAxis from '@/components/Charts/ChartAxis.vue'
import ChartSeries from '@/components/Charts/ChartSeries.vue'
import ChartLegend from '@/components/Charts/ChartLegend.vue'
import ChartTooltip from '@/components/Charts/ChartTooltip.vue'

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
</script>

<template>
	<Chart :title="props.title" :subtitle="props.subtitle">
		<ChartGrid>
			<ChartLegend bottom="bottom" />
			<ChartAxis
				axisType="xAxis"
				type="category"
				:axisTick="false"
				:data="props.data.labels"
			/>
			<ChartAxis axisType="yAxis" type="value" splitLine-lineStyle-type="dashed" />
			<ChartSeries
				v-for="dataset in props.data.datasets"
				:name="dataset.label"
				:data="dataset.data"
				type="line"
				:smooth="props.options.smoothLines"
				:showSymbol="props.options.showPoints"
			/>
			<ChartTooltip trigger="axis" :appendToBody="true" />
		</ChartGrid>
	</Chart>
</template>
