<script setup>
import * as echarts from 'echarts'
import { getColors } from '@/utils/colors'
import { onMounted, ref, reactive, onBeforeUnmount, provide, watch, useAttrs } from 'vue'

const options = reactive({
	fontFamily: 'Inter',
	color: getColors(),
	animation: false,
})
provide('options', options)

const attributes = useAttrs()
watch(() => attributes, updateOptions, { deep: true, immediate: true })
function updateOptions(newAttributes) {
	const { chartTitle, chartSubtitle, ...rest } = newAttributes
	Object.assign(options, rest)
}

const chartRef = ref(null)
let chart = null
onMounted(() => {
	chart = echarts.init(chartRef.value, 'light', {
		renderer: 'canvas',
	})
	setOption(options)
})
watch(options, setOption, { deep: true })
function setOption() {
	chart && chart.setOption(options)
}

const resizeObserver = new ResizeObserver(() => chart.resize())
onMounted(() =>
	setTimeout(() => {
		chartRef.value && resizeObserver.observe(chartRef.value)
	}, 1000)
)
onBeforeUnmount(() => resizeObserver.unobserve(chartRef.value))

function convertAttributesToOptions(attributes) {
	return Object.keys(attributes).reduce((acc, key) => {
		if (key.includes('-')) {
			// options like "splitLines-lineStyle-type = 'dashed'"
			// construct the object from the keys by splitting on '-'
			// eg. { splitLines: { lineStyle: { type: 'dashed' } } }
			// and append it to the accumulator
			const keys = key.split('-') // ['splitLines', 'lineStyle', 'type']
			const value = attributes[key] // 'dashed'
			const lastKey = keys.pop() // 'type'
			const lastObject = keys.reduce((acc, key) => {
				acc[key] = acc[key] || {}
				return acc[key]
			}, acc) // { splitLines: { lineStyle: {} } }
			lastObject[lastKey] = value // { splitLines: { lineStyle: { type: 'dashed' } } }
			return acc
		}
		return { ...acc, [key]: attributes[key] }
	}, {})
}
provide('convertAttributesToOptions', convertAttributesToOptions)

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
	<div class="h-full w-full rounded-md p-2">
		<div class="flex h-full w-full flex-col">
			<div
				v-if="$attrs.chartTitle"
				v-bind="$attrs"
				class="flex-shrink-0"
				:class="['mx-3', $attrs.chartSubtitle ? 'h-11' : 'h-6']"
			>
				<div class="text-lg font-normal leading-6 text-gray-800">
					{{ $attrs.chartTitle }}
				</div>
				<div v-if="$attrs.chartSubtitle" class="text-base font-light">
					{{ $attrs.chartSubtitle }}
				</div>
			</div>
			<div ref="chartRef" class="w-full flex-1 overflow-hidden">
				<slot></slot>
			</div>
		</div>
	</div>
</template>
