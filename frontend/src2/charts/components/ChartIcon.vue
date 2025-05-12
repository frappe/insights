<script setup lang="ts">
import {
	AreaChart,
	BarChart3,
	BarChartHorizontal,
	BatteryMedium,
	Filter,
	Hash,
	LifeBuoy,
	LineChart,
	ScatterChart,
	Table2,
} from 'lucide-vue-next'
import { computed } from 'vue'
import { ChartType } from '../../types/chart.types'

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
		case 'Number':
			return Hash
		default:
			return BarChart3
	}
})
</script>

<template>
	<component :is="icon" class="h-4 w-4 text-gray-700" stroke-width="1.5" v-bind="$attrs" />
</template>
