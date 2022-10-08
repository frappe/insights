<script setup>
import { ref } from 'vue'

import Chart from '@/components/Charts/Chart.vue'
import ChartTitle from '@/components/Charts/ChartTitle.vue'
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
	<Chart fontFamily="Inter">
		<ChartTitle :title="props.title" :subtitle="props.subtitle"></ChartTitle>
		<ChartGrid bottom="55"></ChartGrid>
		<ChartAxis
			axisType="xAxis"
			type="category"
			:axisTick="false"
			:data="props.data.labels"
		></ChartAxis>
		<ChartAxis axisType="yAxis" type="value" splitLine-lineStyle-type="dashed"></ChartAxis>
		<ChartSeries
			v-for="dataset in props.data.datasets"
			:name="dataset.label"
			:data="dataset.data"
			type="line"
			:smooth="props.options.smoothLines"
			:showSymbol="props.options.showPoints"
		>
		</ChartSeries>
		<ChartLegend bottom="0"></ChartLegend>
		<ChartTooltip trigger="axis" :appendToBody="true"></ChartTooltip>
	</Chart>
</template>
