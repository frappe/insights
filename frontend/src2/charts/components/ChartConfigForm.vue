<script setup lang="ts">
import { computed, inject } from 'vue'
import useQuery, { Query } from '../../query/query'
import {
	BarChartConfig,
	DonutChartConfig,
	FunnelChartConfig,
	LineChartConfig,
	NumberChartConfig,
	TableChartConfig,
} from '../../types/chart.types'
import { DimensionOption } from '../../types/query.types'
import { Chart } from '../chart'
import BarChartConfigForm from './BarChartConfigForm.vue'
import DonutChartConfigForm from './DonutChartConfigForm.vue'
import FunnelChartConfigForm from './FunnelChartConfigForm.vue'
import LineChartConfigForm from './LineChartConfigForm.vue'
import NumberChartConfigForm from './NumberChartConfigForm.vue'
import TableChartConfigForm from './TableChartConfigForm.vue'

const props = defineProps<{ chart: Chart }>()

const chartQuery = computed(() => {
	if (!props.chart.doc.query) return {} as Query
	return useQuery(props.chart.doc.query)
})

const dimensions = computed<DimensionOption[]>(() => {
	if (!chartQuery.value.dimensions) return []
	return chartQuery.value.dimensions.map((dimension) => ({
		...dimension,
		label: dimension.column_name,
		value: dimension.column_name,
	}))
})

const columnOptions = computed(() => chartQuery.value.result?.columnOptions || [])
</script>

<template>
	<NumberChartConfigForm
		v-if="props.chart.doc.chart_type == 'Number'"
		v-model="(props.chart.doc.config as NumberChartConfig)"
		:dimensions="dimensions"
		:column-options="columnOptions"
	/>
	<DonutChartConfigForm
		v-if="props.chart.doc.chart_type == 'Donut'"
		v-model="(props.chart.doc.config as DonutChartConfig)"
		:dimensions="dimensions"
		:column-options="columnOptions"
	/>
	<FunnelChartConfigForm
		v-if="props.chart.doc.chart_type == 'Funnel'"
		v-model="(props.chart.doc.config as FunnelChartConfig)"
		:dimensions="dimensions"
		:column-options="columnOptions"
	/>
	<TableChartConfigForm
		v-if="props.chart.doc.chart_type == 'Table'"
		v-model="(props.chart.doc.config as TableChartConfig)"
		:dimensions="dimensions"
		:column-options="columnOptions"
	/>
	<BarChartConfigForm
		v-if="props.chart.doc.chart_type == 'Bar' || props.chart.doc.chart_type == 'Row'"
		v-model="(props.chart.doc.config as BarChartConfig)"
		:dimensions="dimensions"
		:column-options="columnOptions"
	/>
	<LineChartConfigForm
		v-if="props.chart.doc.chart_type == 'Line'"
		v-model="(props.chart.doc.config as LineChartConfig)"
		:dimensions="dimensions"
		:column-options="columnOptions"
	/>
</template>
