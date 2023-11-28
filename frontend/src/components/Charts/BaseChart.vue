<script setup>
import { areDeeplyEqual } from '@/utils'
import * as echarts from 'echarts'
import { onBeforeUnmount, onMounted, onUpdated, ref, watch } from 'vue'

const props = defineProps({
	title: { type: String, required: false },
	subtitle: { type: String, required: false },
	options: { type: Object, required: true },
})

let eChart = null
const chartRef = ref(null)
onMounted(() => {
	eChart = echarts.init(chartRef.value, 'light', { renderer: 'svg' })
	Object.keys(props.options).length && eChart.setOption(props.options)

	const resizeObserver = new ResizeObserver(() => eChart.resize())
	setTimeout(() => chartRef.value && resizeObserver.observe(chartRef.value), 1000)
	onBeforeUnmount(() => chartRef.value && resizeObserver.unobserve(chartRef.value))
})

watch(
	() => props.options,
	(newOptions, oldOptions) => {
		if (!eChart) return
		if (JSON.stringify(newOptions) === JSON.stringify(oldOptions)) return
		if (areDeeplyEqual(newOptions, oldOptions)) return
		eChart.clear()
		eChart.setOption(props.options)
	},
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
	<div class="h-full w-full rounded p-2">
		<div class="flex h-full w-full flex-col">
			<div
				v-if="title"
				class="mt-1 flex-shrink-0"
				:class="['mx-3', subtitle ? 'h-11' : 'h-6']"
			>
				<div class="text-lg font-medium leading-6 text-gray-800">
					{{ title }}
				</div>
				<div v-if="subtitle" class="text-base font-light">
					{{ subtitle }}
				</div>
			</div>
			<div ref="chartRef" class="w-full flex-1 overflow-hidden">
				<slot></slot>
			</div>
		</div>
	</div>
</template>
