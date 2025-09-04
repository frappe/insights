<script setup>
import * as echarts from 'echarts'
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { wheneverChanges } from '../../helpers'
import ChartTitle from './ChartTitle.vue'
import indiaGeoJSON from '../../assets/maps_json/india.json'
import countriesGeoJSON from '../../assets/maps_json/countries.json'
import citiesGeoJSON from '../../assets/maps_json/INDIA_DISTRICTS.json'

echarts.registerMap('india', indiaGeoJSON)
echarts.registerMap('countries', countriesGeoJSON)
echarts.registerMap('cities', citiesGeoJSON)

const props = defineProps({
	title: { type: String, required: false },
	subtitle: { type: String, required: false },
	options: { type: Object, required: true },
	onClick: { type: Function, required: false },
	map: { type: String, required: false },
	filteredCitiesGeoJSON: { type: Object, required: false },
})

let eChart = null
const chartRef = ref(null)
onMounted(() => {
	eChart = echarts.init(chartRef.value, 'light', { renderer: 'canvas' })

	// register filtered cities map if provided
	if (props.filteredCitiesGeoJSON) {
		echarts.registerMap('filtered_cities', props.filteredCitiesGeoJSON)
	}

	Object.keys(props.options).length && eChart.setOption({ ...props.options })
	props.onClick && eChart.on('click', props.onClick)

	const resizeObserver = new ResizeObserver(() => eChart.resize())
	setTimeout(() => chartRef.value && resizeObserver.observe(chartRef.value), 1000)
	onBeforeUnmount(() => chartRef.value && resizeObserver.unobserve(chartRef.value))
})

wheneverChanges(
	() => props.options,
	() => {
		if (props.filteredCitiesGeoJSON) {
			echarts.registerMap('filtered_cities', props.filteredCitiesGeoJSON)
		}
		if (eChart) {
			eChart.setOption({ ...props.options })
		}
	},
	{ deep: true }
)

wheneverChanges(
	() => props.filteredCitiesGeoJSON,
	() => {
		if (props.filteredCitiesGeoJSON && eChart) {
			echarts.registerMap('filtered_cities', props.filteredCitiesGeoJSON)
		}
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
	<div class="flex h-full w-full flex-col rounded">
		<ChartTitle v-if="title" :title="title" />
		<div ref="chartRef" class="w-full flex-1 overflow-hidden">
			<slot></slot>
		</div>
	</div>
</template>
