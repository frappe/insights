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
const options = reactive({
	...defaults,
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
	<div v-bind="$attrs" :class="['mx-3', subtitle ? 'h-11' : 'h-6']">
		<div class="text-xl font-medium leading-6">{{ title }}</div>
		<div v-if="subtitle" class="text-base font-light">
			{{ subtitle }}
		</div>
	</div>
	<div
		ref="chartRef"
		:class="['w-full', subtitle ? 'h-[calc(100%-2.75rem)]' : 'h-[calc(100%-1.5rem)]']"
	>
		<slot></slot>
	</div>
</template>
