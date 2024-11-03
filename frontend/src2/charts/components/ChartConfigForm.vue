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

export type DimensionOption = Dimension & { label: string; value: string }
const dimensions = computed<DimensionOption[]>(() => {
	return props.chart.baseQuery.dimensions.map((dimension) => ({
		...dimension,
		label: dimension.column_name,
		value: dimension.column_name,
	}))
})

export type MeasureOption = Measure & { label: string; value: string }
const measures = computed<MeasureOption[]>(() => {
	const queryMeasures = props.chart.baseQuery.measures.map((measure) => ({
		...measure,
		label: measure.measure_name,
		value: measure.measure_name,
	}))
	const chartMeasures = Object.values(props.chart.doc.calculated_measures || {}).map(
		(measure) => ({
			...measure,
			label: measure.measure_name,
			value: measure.measure_name,
		})
	)
	return [...queryMeasures, ...chartMeasures]
})
</script>

<template>
	<NumberChartConfigForm
		v-if="props.chart.doc.chart_type == 'Number'"
		v-model="(props.chart.doc.config as NumberChartConfig)"
		:dimensions="dimensions"
		:measures="measures"
	/>
	<DonutChartConfigForm
		v-if="props.chart.doc.chart_type == 'Donut'"
		v-model="(props.chart.doc.config as DountChartConfig)"
		:dimensions="dimensions"
		:measures="measures"
	/>
	<FunnelChartConfigForm
		v-if="props.chart.doc.chart_type == 'Funnel'"
		v-model="(props.chart.doc.config as FunnelChartConfig)"
		:dimensions="dimensions"
		:measures="measures"
	/>
	<TableChartConfigForm
		v-if="props.chart.doc.chart_type == 'Table'"
		v-model="(props.chart.doc.config as TableChartConfig)"
		:dimensions="dimensions"
		:measures="measures"
	/>
	<BarChartConfigForm
		v-if="props.chart.doc.chart_type == 'Bar' || props.chart.doc.chart_type == 'Row'"
		v-model="(props.chart.doc.config as BarChartConfig)"
		:dimensions="dimensions"
		:measures="measures"
	/>
	<LineChartConfigForm
		v-if="props.chart.doc.chart_type == 'Line'"
		v-model="(props.chart.doc.config as LineChartConfig)"
		:dimensions="dimensions"
		:measures="measures"
	/>
</template>
