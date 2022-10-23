<script setup>
import * as echarts from 'echarts'
import { getColors } from '@/utils/charts/colors'
import { onMounted, ref, reactive, onBeforeUnmount, provide, watch, useAttrs } from 'vue'

const chartRef = ref(null)
const { title, subtitle, ...attributes } = useAttrs()

const defaults = {
	fontFamily: 'Inter',
	color: getColors(),
}
const options = reactive({ ...defaults, ...attributes })
provide('options', options)

let chart = null
defineExpose({
	downloadChart: () => {
		const image = new Image()
		const type = 'png'
		image.src = chart.getDataURL({
			type,
			pixelRatio: 2,
			backgroundColor: '#fff',
		})
		const link = document.createElement('a')
		link.href = image.src
		link.download = `${title}.${type}`
		link.click()
	},
})
onMounted(() => {
	chart = echarts.init(chartRef.value, 'light', {
		renderer: 'canvas',
	})
	setOption(options)
})
watch(options, setOption, { deep: true })

function setOption(options) {
	chart && chart.setOption(options)
}

const resizeObserver = new ResizeObserver(() => {
	chart.resize()
})
onMounted(() => {
	setTimeout(() => {
		chartRef.value && resizeObserver.observe(chartRef.value)
	}, 1000)
})
onBeforeUnmount(() => {
	resizeObserver.unobserve(chartRef.value)
})

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
</script>

<template>
	<div class="h-full w-full rounded-md border px-2 py-3">
		<div v-bind="$attrs" :class="['mx-3', $attrs.subtitle ? 'h-11' : 'h-6']">
			<div class="text-lg font-normal leading-6 text-gray-800">{{ $attrs.title }}</div>
			<div v-if="$attrs.subtitle" class="text-base font-light">
				{{ $attrs.subtitle }}
			</div>
		</div>
		<div
			ref="chartRef"
			:class="['w-full', subtitle ? 'h-[calc(100%-2.75rem)]' : 'h-[calc(100%-1.5rem)]']"
		>
			<slot></slot>
		</div>
	</div>
</template>
