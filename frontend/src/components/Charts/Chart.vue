<script setup>
import { getColors } from '@/utils/colors'
import * as echarts from 'echarts'
import { onBeforeUnmount, onMounted, provide, reactive, ref, watch, computed } from 'vue'

const options = reactive({
	// fontFamily: 'Inter',
	color: getColors(),
	animation: false,
})
provide('options', options)
watch(options, setOption, { deep: true })
function setOption() {
	chart && chart.setOption(options)
}

const props = defineProps({ options: Object, default: () => ({}) })
const chartTitle = computed(() => props.options?.chartTitle)
const chartSubtitle = computed(() => props.options?.chartSubtitle)

watch(() => props.options, updateOptions, { deep: true, immediate: true })
function updateOptions(newOptions) {
	const { chartTitle, chartSubtitle, ...rest } = newOptions
	Object.assign(options, rest)
}

let chart = null
const chartRef = ref(null)
onMounted(() => {
	chart = echarts.init(chartRef.value, 'light', { renderer: 'svg' })
	setOption(options)
})

const resizeObserver = new ResizeObserver(() => chart.resize())
onMounted(() =>
	setTimeout(() => {
		chartRef.value && resizeObserver.observe(chartRef.value)
	}, 1000)
)
onBeforeUnmount(() => chartRef.value && resizeObserver.unobserve(chartRef.value))

defineExpose({ downloadChart })
function downloadChart() {
	const image = new Image()
	const type = 'png'
	image.src = chart.getDataURL({
		type,
		pixelRatio: 2,
		backgroundColor: '#fff',
	})
	const link = document.createElement('a')
	link.href = image.src
	link.download = `${attributes.title}.${type}`
	link.click()
}
</script>

<template>
	<div class="h-full w-full rounded p-2">
		<div class="flex h-full w-full flex-col">
			<div
				v-if="chartTitle"
				class="flex-shrink-0"
				:class="['mx-3', chartSubtitle ? 'h-11' : 'h-6']"
			>
				<div class="text-lg font-normal leading-6 text-gray-800">
					{{ chartTitle }}
				</div>
				<div v-if="chartSubtitle" class="text-base font-light">
					{{ chartSubtitle }}
				</div>
			</div>
			<div ref="chartRef" class="w-full flex-1 overflow-hidden">
				<slot></slot>
			</div>
		</div>
	</div>
</template>
