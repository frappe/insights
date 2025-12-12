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
    // Choose renderer (map requires canvas)
    const isMap = props.options?.series?.some(s => s.type === 'map')
    const renderer = isMap ? 'canvas' : 'svg'

    eChart = echarts.init(chartRef.value, 'light', { renderer })

    if (Object.keys(props.options).length) {
        eChart.setOption(props.options)
    }

    if (props.onClick) {
        eChart.on('click', props.onClick)
    }

    // Auto-resize chart
    resizeObserver = new ResizeObserver(() => {
        try {
            eChart?.resize()
        } catch (_) {}
    })

    setTimeout(() => {
        chartRef.value && resizeObserver.observe(chartRef.value)
    }, 500)
})

onBeforeUnmount(() => {
    chartRef.value && resizeObserver?.unobserve(chartRef.value)
})

wheneverChanges(() => props.options, setChartOptions, { deep: true })

async function setChartOptions() {
    if (!eChart) return

    const mapSeries = props.options?.series?.find(s => s.type === 'map')
    if (mapSeries) {
        await registerMap(mapSeries.map)
    }

    eChart.setOption({ ...props.options })
}

// Load map JSON file when required
async function registerMap(mapName) {
    try {
        const res = await fetch(`/assets/insights/maps/${mapName}.json`)
        const geoJson = await res.json()
        echarts.registerMap(mapName, geoJson)
    } catch (e) {
        console.warn("Map load failed:", mapName)
    }
}
</script>

<template>
    <div class="flex h-full w-full flex-col rounded">
        <ChartTitle v-if="title" :title="title" :subtitle="subtitle" />
        <div ref="chartRef" class="w-full flex-1 overflow-hidden"></div>
    </div>
</template>
