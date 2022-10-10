<script setup>
import { reactive, ref, computed } from 'vue'
import Chart from '@/components/Charts/Chart.vue'
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

const dataset = computed(() => props.data.datasets?.[0])
const data = computed(() => {
	const slices = dataset.value?.data.slice(0, parseInt(props.options.maxSlices) || 9)
	const otherSlices = dataset.value?.data
		.slice(parseInt(props.options.maxSlices) || 9)
		.reduce((a, b) => a + b, 0)

	const _data = slices.map((value, index) => {
		return {
			name: props.data.labels[index],
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
	pageIconSize: 12,
	pageIconColor: '#64748B',
	pageIconInactiveColor: '#C0CCDA',
	pageFormatter: '{current}',
	pageButtonItemGap: 2,
})
const center = ref(['50%', '45%'])
const radius = ref('75%')

if (props.options.labelPosition?.value) {
	const position = props.options.labelPosition.value
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
			center.value[1] = '60%'
			legendOptions.padding = 20
			break
		case 'Bottom':
			radius.value = '75%'
			legendOptions.bottom = 0
			legendOptions.left = 'center'
			center.value[1] = '45%'
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
</script>

<template>
	<Chart :title="props.title" :subtitle="props.subtitle">
		<ChartSeries
			type="pie"
			:name="dataset.label"
			:data="data"
			:center="center"
			:radius="radius"
			:labelLine-show="false"
			:label-show="false"
			:emphasis-scaleSize="5"
		/>
		<ChartTooltip trigger="item" :appendToBody="true" />
		<ChartLegend v-bind="legendOptions" />
	</Chart>
</template>
