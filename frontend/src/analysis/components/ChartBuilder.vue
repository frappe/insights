<script setup lang="ts">
import { Analysis, analysisKey } from '@/analysis/useAnalysis'
import { LoadingIndicator } from 'frappe-ui'
import { inject } from 'vue'
import { useAnalysisChart } from '../useAnalysisChart'
import AxisChartConfigForm from './AxisChartConfigForm.vue'
import ChartRenderer from './ChartRenderer.vue'
import ChartTypeSelector from './ChartTypeSelector.vue'
import DataTable from './DataTable.vue'
import DonutChartConfigForm from './DonutChartConfigForm.vue'
import MetricChartConfigForm from './MetricChartConfigForm.vue'
import TableChartConfigForm from './TableChartConfigForm.vue'
import {
	AXIS_CHARTS,
	AxisChartConfig,
	DountChartConfig,
	MetricChartConfig,
	TableChartConfig,
} from './chart_utils'

const props = defineProps<{ chartName: string }>()
const analysis = inject(analysisKey) as Analysis

const analysisChart = useAnalysisChart(props.chartName, analysis.model)
</script>

<template>
	<div class="relative flex h-full w-full divide-x overflow-hidden">
		<div class="relative flex w-[16rem] flex-shrink-0 flex-col overflow-y-auto bg-white">
			<ChartTypeSelector v-model="analysisChart.type" />
			<hr class="my-1 border-t border-gray-200" />
			<MetricChartConfigForm
				v-if="analysisChart.type == 'Metric'"
				v-model="(analysisChart.config as MetricChartConfig)"
				:dimensions="analysis.model.dimensions"
				:measures="analysis.model.measures"
			/>
			<DonutChartConfigForm
				v-if="analysisChart.type == 'Donut'"
				v-model="(analysisChart.config as DountChartConfig)"
				:dimensions="analysis.model.dimensions"
				:measures="analysis.model.measures"
			/>
			<TableChartConfigForm
				v-if="analysisChart.type == 'Table'"
				v-model="(analysisChart.config as TableChartConfig)"
				:dimensions="analysis.model.dimensions"
				:measures="analysis.model.measures"
			/>
			<AxisChartConfigForm
				v-if="AXIS_CHARTS.includes(analysisChart.type)"
				v-model="(analysisChart.config as AxisChartConfig)"
				:chart-type="analysisChart.type"
				:dimensions="analysis.model.dimensions"
				:measures="analysis.model.measures"
			/>
		</div>
		<div class="relative flex h-full w-full flex-col divide-y overflow-hidden">
			<div
				v-if="analysisChart.query.executing"
				class="absolute top-0 left-0 z-10 flex h-full w-full items-center justify-center rounded bg-gray-50/30 backdrop-blur-sm"
			>
				<LoadingIndicator class="h-8 w-8 text-gray-700" />
			</div>
			<div class="flex flex-1 flex-shrink-0 items-center justify-center overflow-hidden">
				<ChartRenderer :chart="analysisChart" />
			</div>
			<div
				v-if="analysisChart.type != 'Table'"
				class="flex max-h-[16rem] min-h-[5rem] flex-1 flex-shrink-0 flex-col"
			>
				<DataTable
					:columns="analysisChart.query.result.columns"
					:rows="analysisChart.query.result.rows"
				/>
			</div>
		</div>
	</div>
</template>
