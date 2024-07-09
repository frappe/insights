<script setup lang="ts">
import { LineChartConfig } from '../../types/chart.types'
import { Dimension, Measure } from '../../types/query.types'
import AxisChartConfigForm from './AxisChartConfigForm.vue'

const props = defineProps<{
	dimensions: Dimension[]
	measures: Measure[]
}>()

const config = defineModel<LineChartConfig>({
	required: true,
	default: () => ({
		x_axis: {},
		y_axis: [],
		y2_axis: [],
		y2_axis_type: 'line',
		split_by: {},
		show_data_labels: false,
	}),
})
</script>

<template>
	<AxisChartConfigForm
		v-model="config"
		:dimensions="props.dimensions"
		:measures="props.measures"
	/>
</template>
