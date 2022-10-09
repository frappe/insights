<template>
	<div ref="chartRef" class="h-full w-full">
		<slot></slot>
	</div>
</template>

<script setup>
import * as echarts from 'echarts'
import { onMounted, ref, reactive, onBeforeUnmount, provide, watch, useAttrs } from 'vue'

const chartRef = ref(null)
const attributes = useAttrs()
const options = reactive({
	fontFamily: 'Inter',
	...attributes,
})
provide('options', options)

let chart
onMounted(() => {
	chart = echarts.init(chartRef.value, 'light', {
		renderer: 'svg',
	})
	chart.setOption(options)
})

watch(options, (newOptions) => chart && chart.setOption(newOptions), {
	deep: true,
})

const resizeObserver = new ResizeObserver(() => {
	chart.resize()
})
onMounted(() => {
	setTimeout(() => {
		resizeObserver.observe(chartRef.value)
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
			const keys = key.split('-')
			const value = attributes[key]
			return keys.reduceRight((acc, key, index) => {
				if (index === keys.length - 1) {
					return { [key]: value }
				}
				return { [key]: acc }
			}, acc)
		}
		return { ...acc, [key]: attributes[key] }
	}, {})
}
provide('convertAttributesToOptions', convertAttributesToOptions)
</script>
