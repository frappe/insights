<script setup lang="ts">
import { Analysis, analysisKey } from '@/analysis/useAnalysis'
import BaseChart from '@/components/Charts/BaseChart.vue'
import { QueryResultColumn, QueryResultRow } from '@/query/next/useQuery'
import { FIELDTYPES, formatNumber, getShortNumber } from '@/utils'
import { Table2Icon } from 'lucide-vue-next'
import { computed, inject, provide } from 'vue'
import { analysisQueryKey, useAnalysisQuery } from '../useAnalysisQuery'
import ChartBuilderSidebar from './ChartBuilderSidebar.vue'

const props = defineProps<{ chartName: string }>()

const analysis = inject(analysisKey) as Analysis
if (!analysis) throw new Error('Analysis not found')

const analysisQuery = useAnalysisQuery(props.chartName, analysis.model)
provide(analysisQueryKey, analysisQuery)

const guessedChartType = computed(() => {
	return guessChart(analysisQuery.result.columns, analysisQuery.result.rows)
})
function guessChart(columns: QueryResultColumn[], rows: QueryResultRow[]) {
	// first let's categorize the columns into dimensions and measures and then into discrete and continuous
	const dimensions = columns.filter((c) => FIELDTYPES.DIMENSION.includes(c.type))
	const discreteDimensions = dimensions.filter((c) => FIELDTYPES.DISCRETE.includes(c.type))
	const continuousDimensions = dimensions.filter((c) => FIELDTYPES.CONTINUOUS.includes(c.type))

	const measures = columns.filter((c) => FIELDTYPES.MEASURE.includes(c.type))
	const discreteMeasures = measures.filter((c) => FIELDTYPES.DISCRETE.includes(c.type))
	const continuousMeasures = measures.filter((c) => FIELDTYPES.CONTINUOUS.includes(c.type))

	if (measures.length === 1 && dimensions.length === 0) return 'number'
	if (discreteDimensions.length === 1 && measures.length) return 'bar'
	if (continuousDimensions.length === 1 && measures.length) return 'line'
	if (discreteDimensions.length > 1 && measures.length) return 'table'
}

function getLineOrBarChartOptions(
	columns: QueryResultColumn[],
	rows: QueryResultRow[],
	lineOrBar = 'bar'
) {
	const columnNames = columns.map((c) => c.name)
	const data = [
		columns.map((c) => c.name),
		...rows.map((r) => columnNames.map((c) => r[c as keyof QueryResultRow])),
	]
	const maxColumnLabelLength = Math.max(...columns.map((c) => c.name.length))
	const rightOffset = maxColumnLabelLength * 10
	return {
		grid: {
			top: 10,
			left: 10,
			right: rightOffset,
			bottom: 10,
			containLabel: true,
		},
		dataset: { source: data },
		xAxis: { type: 'category' },
		yAxis: {
			type: 'value',
			splitLine: { lineStyle: { type: 'dashed' } },
			axisLabel: { formatter: (value: Number) => getShortNumber(value, 1) },
		},
		series: columns
			.filter((c) => FIELDTYPES.MEASURE.includes(c.type))
			.map((c) => ({ type: lineOrBar })),
		tooltip: {
			trigger: 'axis',
			confine: true,
			appendToBody: false,
			valueFormatter: (value: any) => (isNaN(value) ? value : formatNumber(value)),
		},
		legend: {
			icon: 'circle',
			right: 0,
			orient: 'vertical',
			top: 'top',
		},
	}
}
</script>

<template>
	<div class="relative flex h-full w-full divide-x overflow-hidden">
		<ChartBuilderSidebar />
		<div class="flex h-full w-full flex-col divide-y overflow-hidden">
			<div class="flex flex-1 flex-shrink-0 overflow-hidden p-4">
				<BaseChart
					v-if="guessedChartType === 'bar' || guessedChartType === 'line'"
					:options="
						getLineOrBarChartOptions(
							analysisQuery.result.columns,
							analysisQuery.result.rows,
							guessedChartType
						)
					"
				/>
			</div>
			<div v-if="false" class="flex max-h-[18rem] min-h-[5rem] flex-1 flex-shrink-0 flex-col">
				<div
					v-if="analysisQuery.result.columns?.length || analysisQuery.result.rows?.length"
					class="flex w-full flex-1 overflow-y-auto font-mono text-sm"
				>
					<table class="border-separate border-spacing-0">
						<thead class="sticky top-0 bg-white">
							<tr>
								<td class="border-b border-r py-2 px-3"></td>
								<td
									v-for="(column, idx) in analysisQuery.result.columns"
									:key="idx"
									class="truncate border-b border-r py-2 px-3"
									:class="
										FIELDTYPES.NUMBER.includes(column.type)
											? 'text-right'
											: 'text-left'
									"
									width="150px"
								>
									{{ column.name }}
								</td>
							</tr>
						</thead>
						<tbody>
							<tr v-for="(row, idx) in analysisQuery.result.rows" :key="idx">
								<td class="border-b border-r px-3">{{ idx + 1 }}</td>
								<td
									v-for="(value, idx2) in Object.values(row)"
									:key="idx2"
									class="truncate border-b border-r py-2 px-3 text-gray-800"
									:class="isNaN(value) ? '' : 'text-right'"
								>
									{{ value }}
								</td>
							</tr>
							<tr height="99%" class="border-b"></tr>
						</tbody>
					</table>
				</div>

				<div v-else class="flex h-full w-full items-center justify-center">
					<div class="flex flex-col items-center gap-2">
						<Table2Icon class="h-16 w-16 text-gray-300" stroke-width="1.5" />
						<p class="text-center text-gray-500">No data to display.</p>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>
