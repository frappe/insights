<script setup>
import * as echarts from 'echarts'
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { wheneverChanges } from '../../helpers'
import ChartTitle from './ChartTitle.vue'

const props = defineProps({
	title: { type: String, required: false },
	subtitle: { type: String, required: false },
	options: { type: Object, required: true },
	onClick: { type: Function, required: false },
})

let eChart = null
const chartRef = ref(null)
onMounted(() => {
	eChart = echarts.init(chartRef.value, 'light', { renderer: 'svg' })
	Object.keys(props.options).length && eChart.setOption({ ...props.options })
	props.onClick && eChart.on('click', props.onClick)

	const resizeObserver = new ResizeObserver(() => eChart.resize())
	setTimeout(() => chartRef.value && resizeObserver.observe(chartRef.value), 1000)
	onBeforeUnmount(() => chartRef.value && resizeObserver.unobserve(chartRef.value))
})

wheneverChanges(
	() => props.options,
	() => eChart.setOption({ ...props.options }),
	{ deep: true }
)

defineExpose({ downloadChart })
function downloadChart() {
	const image = new Image()
	const type = 'png'
	image.src = eChart.getDataURL({
		type,
		pixelRatio: 2,
		backgroundColor: '#fff',
	})
	const link = document.createElement('a')
	link.href = image.src
	link.download = `${props.title}.${type}`
	link.click()
}
</script>

<template>
	<div class="flex h-full w-full flex-col rounded">
		<ChartTitle v-if="title" :title="title" />
		<div ref="chartRef" class="w-full flex-1 overflow-hidden">
			<slot></slot>
		</div>
	</div>
</template>
