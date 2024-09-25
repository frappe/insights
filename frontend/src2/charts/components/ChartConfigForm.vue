<script setup lang="ts">
import { computed } from 'vue'
import InlineFormControlLabel from '../../components/InlineFormControlLabel.vue'
import { Dimension, Measure } from '../../types/query.types'
import { Chart } from '../chart'
import BarChartConfigForm from './BarChartConfigForm.vue'
import DonutChartConfigForm from './DonutChartConfigForm.vue'
import LineChartConfigForm from './LineChartConfigForm.vue'
import NumberChartConfigForm from './NumberChartConfigForm.vue'
import TableChartConfigForm from './TableChartConfigForm.vue'
import {
	BarChartConfig,
	DountChartConfig,
	FunnelChartConfig,
	LineChartConfig,
	NumberChartConfig,
	TableChartConfig,
} from '../../types/chart.types'
import FunnelChartConfigForm from './FunnelChartConfigForm.vue'

const props = defineProps<{ chart: Chart }>()
const chart = props.chart

export type DimensionOption = Dimension & { label: string; value: string }
const dimensions = computed<DimensionOption[]>(() => {
	return chart.baseQuery.dimensions.map((dimension) => ({
		...dimension,
		label: dimension.column_name,
		value: dimension.column_name,
	}))
})

export type MeasureOption = Measure & { label: string; value: string }
const measures = computed<MeasureOption[]>(() => {
	return chart.baseQuery.measures.map((measure) => ({
		...measure,
		label: measure.measure_name,
		value: measure.measure_name,
	}))
})
</script>

<template>
	<NumberChartConfigForm
		v-if="chart.doc.chart_type == 'Number'"
		v-model="(chart.doc.config as NumberChartConfig)"
		:dimensions="dimensions"
		:measures="measures"
	/>
	<DonutChartConfigForm
		v-if="chart.doc.chart_type == 'Donut'"
		v-model="(chart.doc.config as DountChartConfig)"
		:dimensions="dimensions"
		:measures="measures"
	/>
	<FunnelChartConfigForm
		v-if="chart.doc.chart_type == 'Funnel'"
		v-model="(chart.doc.config as FunnelChartConfig)"
		:dimensions="dimensions"
		:measures="measures"
	/>
	<TableChartConfigForm
		v-if="chart.doc.chart_type == 'Table'"
		v-model="(chart.doc.config as TableChartConfig)"
		:dimensions="dimensions"
		:measures="measures"
	/>
	<BarChartConfigForm
		v-if="chart.doc.chart_type == 'Bar'"
		v-model="(chart.doc.config as BarChartConfig)"
		:dimensions="dimensions"
		:measures="measures"
	/>
	<LineChartConfigForm
		v-if="chart.doc.chart_type == 'Line'"
		v-model="(chart.doc.config as LineChartConfig)"
		:dimensions="dimensions"
		:measures="measures"
	/>
</template>
