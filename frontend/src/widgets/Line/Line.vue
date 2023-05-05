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

const shouldRender = computed(() => {
	return !!labels.value.length && !!datasets.value.length
})

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
			<ChartAxis axisType="xAxis" type="category" :axisTick="false" :data="labels" />
			<ChartAxis axisType="yAxis" type="value" splitLine-lineStyle-type="dashed" />
			<ChartSeries
				v-for="dataset in datasets"
				:name="dataset.label"
				:data="dataset.data"
				type="line"
				:smooth="props.options.smoothLines ? 0.4 : false"
				:smoothMonotone="'x'"
				:showSymbol="props.options.showPoints"
				:markLine="markLine"
				:areaStyle="{ opacity: props.options.showArea ? 0.1 : 0 }"
			/>
			<ChartTooltip />
		</ChartGrid>
	</Chart>
	<template v-else>
		<slot name="placeholder"></slot>
	</template>
</template>
