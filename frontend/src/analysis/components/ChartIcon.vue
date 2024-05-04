<script setup lang="ts">
import {
	AreaChart,
	BarChart3,
	BarChartHorizontal,
	BatteryMedium,
	Filter,
	LifeBuoy,
	LineChart,
	ScatterChart,
	Table2,
} from 'lucide-vue-next'
import { computed } from 'vue'
import { ChartType } from './chart_utils'

const props = defineProps<{ chartType: ChartType }>()
const icon = computed(() => {
	switch (props.chartType) {
		case 'Bar':
			return BarChart3
		case 'Line':
			return LineChart
		case 'Row':
			return BarChartHorizontal
		case 'Scatter':
			return ScatterChart
		case 'Area':
			return AreaChart
		case 'Donut':
			return LifeBuoy
		case 'Funnel':
			return Filter
		case 'Table':
			return Table2
		case 'Metric':
			return BatteryMedium
		default:
			throw new Error(`Unknown chart type: ${props.chartType}`)
	}
})
</script>

<template>
	<component :is="icon" class="h-4 w-4 text-gray-700" stroke-width="1.5" />
</template>
