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
let resizeObserver = null

onMounted(async () => {
	const series = props.options?.series?.find((s) => s.type === 'map')
	const isMap = series && series.type === 'map'
	const renderer = isMap ? 'canvas' : 'svg'
	eChart = echarts.init(chartRef.value, 'light', { renderer })

	await setChartOptions()
	props.onClick && eChart.on('click', props.onClick)

	resizeObserver = new ResizeObserver(() => eChart.resize())
	setTimeout(
		() => chartRef.value && resizeObserver && resizeObserver.observe(chartRef.value),
		1000,
	)
})

onBeforeUnmount(() => {
	if (chartRef.value && resizeObserver) resizeObserver.unobserve(chartRef.value)
})

wheneverChanges(() => props.options, setChartOptions, { deep: true })

async function setChartOptions() {
	if (!eChart) return
	const series = props.options?.series?.find((s) => s.type === 'map')
	const isMap = series && series.type === 'map'
	if (isMap) {
		await registerMap(series.map)
	}
	eChart.setOption({ ...props.options })
}

async function registerMap(mapName) {
	if (!mapName) return
	if (mapName === 'india') {
		const mapJson = await import('../../assets/maps_json/india.json')
		echarts.registerMap('india', mapJson.default)
	} else if (mapName === 'world') {
		const mapJson = await import('../../assets/maps_json/world_map.json')
		echarts.registerMap('world', mapJson.default)
	}
}

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
