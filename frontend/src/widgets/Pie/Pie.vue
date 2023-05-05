<script setup>
import Chart from '@/components/Charts/Chart.vue'
import ChartLegend from '@/components/Charts/ChartLegend.vue'
import ChartSeries from '@/components/Charts/ChartSeries.vue'
import ChartTooltip from '@/components/Charts/ChartTooltip.vue'
import { whenever } from '@vueuse/core'
import { computed, inject, reactive, ref } from 'vue'

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
const dataset = computed(() => {
	if (!results.value?.length || !props.options.yAxis) return {}
	const columns = results.value[0].map((d) => d.label)
	const columnIndex = columns.indexOf(props.options.yAxis)
	return {
		label: props.options.yAxis,
		data: results.value.slice(1).map((d) => d[columnIndex]),
	}
})

const shouldRender = computed(() => {
	return !!labels.value.length && !!dataset.value.label
})

const MAX_SLICES = 9
const data = computed(() => {
	const slices = dataset.value?.data.slice(0, parseInt(props.options.maxSlices) || MAX_SLICES)
	const otherSlices = dataset.value?.data
		.slice(parseInt(props.options.maxSlices) || 9)
		.reduce((a, b) => a + b, 0)

	const _data = slices.map((value, index) => {
		return {
			name: labels.value[index],
			value: value,
		}
	})
	if (otherSlices) {
		_data.push({
			name: 'Others',
			value: otherSlices,
		})
	}
	return _data
})

const legendOptions = reactive({
	type: 'plain',
	bottom: 0,
})
const center = ref(['50%', '50%'])
const radius = ref('75%')

if (!props.options.inlineLabels && props.options.labelPosition) {
	const position = props.options.labelPosition
	updateLegendOptions(position)
}

function updateLegendOptions(position) {
	legendOptions.type = props.options.scrollLabels ? 'scroll' : 'plain'
	legendOptions.orient = position === 'Top' || position === 'Bottom' ? 'horizontal' : 'vertical'

	switch (position) {
		case 'Top':
			radius.value = '75%'
			legendOptions.top = 0
			legendOptions.left = 'center'
			center.value = ['50%', '60%']
			legendOptions.padding = 20
			break
		case 'Bottom':
			radius.value = '75%'
			legendOptions.bottom = 0
			legendOptions.left = 'center'
			center.value = ['50%', '45%']
			legendOptions.padding = [20, 20, 10, 20]
			break
		case 'Right':
			radius.value = '85%'
			center.value = ['35%', '50%']
			legendOptions.left = '65%'
			legendOptions.top = 'middle'
			legendOptions.padding = [20, 0, 20, 0]
			break
		case 'Left':
			radius.value = '85%'
			center.value = ['65%', '50%']
			legendOptions.right = '65%'
			legendOptions.top = 'middle'
			legendOptions.padding = [20, 0, 20, 0]
			break
	}
}

function formatLabel({ name, percent }) {
	return `${name} (${percent.toFixed(0)}%)`
}

function formatLegend(name) {
	let total = dataset.value?.data.reduce((a, b) => a + b, 0)
	const labelIndex = labels.value.indexOf(name)

	if (labelIndex === -1 && name == 'Others') {
		const otherSlicesTotal = dataset.value?.data
			.slice(parseInt(props.options.maxSlices) || MAX_SLICES)
			.reduce((a, b) => a + b, 0)
		const percent = (otherSlicesTotal / total) * 100
		return `${name} (${percent.toFixed(0)}%)`
	}

	const percent = (dataset.value?.data[labelIndex] / total) * 100
	return `${name} (${percent.toFixed(0)}%)`
}

function appendPercentage(value) {
	let total = dataset.value?.data.reduce((a, b) => a + b, 0)
	const percent = (value / total) * 100
	return `${value} (${percent.toFixed(0)}%)`
}
</script>

<template>
	<Chart
		v-if="shouldRender"
		ref="eChart"
		:chartTitle="props.options.title"
		:chartSubtitle="props.options.subtitle"
		:color="props.options.colors"
	>
		<ChartSeries
			type="pie"
			:name="dataset.label"
			:data="data"
			:center="center"
			:radius="radius"
			:labelLine-show="props.options.inlineLabels"
			:labelLine-lineStyle-width="2"
			:labelLine-length="10"
			:labelLine-length2="20"
			:labelLine-smooth="true"
			:label-show="props.options.inlineLabels"
			:label-formatter="formatLabel"
			:emphasis-scaleSize="5"
		/>
		<ChartTooltip trigger="item" :appendToBody="true" :valueFormatter="appendPercentage" />
		<ChartLegend
			v-if="!props.options.inlineLabels"
			v-bind="legendOptions"
			:formatter="formatLegend"
		/>
	</Chart>
	<template v-else>
		<slot name="placeholder"></slot>
	</template>
</template>
