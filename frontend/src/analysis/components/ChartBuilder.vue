<script setup lang="ts">
import { Analysis, analysisKey } from '@/analysis/useAnalysis'
import BaseChart from '@/components/Charts/BaseChart.vue'
import { computed, inject } from 'vue'
import { useAnalysisChart } from '../useAnalysisChart'
import AxisChartTypeConfigForm from './AxisChartTypeConfigForm.vue'
import ChartTypeSelector from './ChartTypeSelector.vue'
import DataTable from './DataTable.vue'
import { getLineOrBarChartOptions } from './chart_utils'

const props = defineProps<{ chartName: string }>()
const analysis = inject(analysisKey) as Analysis

const analysisChart = useAnalysisChart(props.chartName, analysis.model)

const eChartOptions = computed(() => {
	if (!analysisChart.data.columns?.length) return
	if (analysisChart.type === 'Bar') {
		return getLineOrBarChartOptions(analysisChart.data.columns, analysisChart.data.rows, 'bar')
	}
	if (analysisChart.type === 'Line') {
		return getLineOrBarChartOptions(analysisChart.data.columns, analysisChart.data.rows, 'line')
	}
})
</script>

<template>
	<div class="relative flex h-full w-full divide-x overflow-hidden">
		<div class="relative flex w-[16rem] flex-shrink-0 flex-col overflow-y-auto bg-white">
			<ChartTypeSelector v-model="analysisChart.type" />
			<hr class="my-1 border-t border-gray-200" />
			<AxisChartTypeConfigForm
				v-if="analysisChart.type"
				v-model="analysisChart.options"
				:chart-type="analysisChart.type"
				:dimensions="analysis.model.dimensions"
				:measures="analysis.model.measures"
			/>
		</div>
		<div class="flex h-full w-full flex-col divide-y overflow-hidden">
			<div class="flex flex-1 flex-shrink-0 overflow-hidden p-4">
				<BaseChart v-if="eChartOptions" :options="eChartOptions" />
			</div>
			<div v-if="true" class="flex max-h-[16rem] min-h-[5rem] flex-1 flex-shrink-0 flex-col">
				<DataTable :columns="analysisChart.data.columns" :rows="analysisChart.data.rows" />
			</div>
		</div>
	</div>
</template>
