<script setup lang="ts">
import InlineFormControlLabel from '../../components/InlineFormControlLabel.vue'
import { AXIS_CHARTS } from '../../types/chart.types'
import { Chart } from '../chart'
import AxisChartConfigForm from './AxisChartConfigForm.vue'
import DonutChartConfigForm from './DonutChartConfigForm.vue'
import NumberChartConfigForm from './NumberChartConfigForm.vue'
import TableChartConfigForm from './TableChartConfigForm.vue'

const props = defineProps<{ chart: Chart }>()
const chart = props.chart
</script>

<template>
	<InlineFormControlLabel label="Title">
		<FormControl v-model="chart.doc.title" />
	</InlineFormControlLabel>
	<NumberChartConfigForm
		v-if="chart.doc.chart_type == 'Number'"
		v-model="chart.doc.config"
		:dimensions="chart.baseQuery.dimensions"
		:measures="chart.baseQuery.measures"
	/>
	<DonutChartConfigForm
		v-if="chart.doc.chart_type == 'Donut'"
		v-model="chart.doc.config"
		:dimensions="chart.baseQuery.dimensions"
		:measures="chart.baseQuery.measures"
	/>
	<TableChartConfigForm
		v-if="chart.doc.chart_type == 'Table'"
		v-model="chart.doc.config"
		:dimensions="chart.baseQuery.dimensions"
		:measures="chart.baseQuery.measures"
	/>
	<AxisChartConfigForm
		v-if="AXIS_CHARTS.includes(chart.doc.chart_type)"
		v-model="chart.doc.config"
		:chart-type="chart.doc.chart_type"
		:dimensions="chart.baseQuery.dimensions"
		:measures="chart.baseQuery.measures"
	/>
</template>
