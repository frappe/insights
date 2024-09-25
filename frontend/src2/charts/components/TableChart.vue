<script setup lang="ts">
import { computed } from 'vue'
import { TableChartConfig } from '../../types/chart.types'
import { Chart } from '../chart'
import DataTable from '../../components/DataTable.vue'
import ChartBuilderTableColumn from './ChartBuilderTableColumn.vue'
import ChartTitle from './ChartTitle.vue'

const props = defineProps<{ chart: Chart }>()

const title = computed(() => props.chart.doc.title)
const config = computed(() => props.chart.doc.config as TableChartConfig)
</script>

<template>
	<div class="flex h-full w-full flex-col overflow-hidden rounded bg-white shadow">
		<ChartTitle v-if="title" :title="title" />
		<DataTable
			v-if="chart.doc.chart_type == 'Table'"
			class="w-full flex-1 overflow-hidden border-t"
			:columns="chart.dataQuery.result.columns"
			:rows="chart.dataQuery.result.formattedRows"
			:show-filter-row="config.show_filter_row"
			:show-column-totals="config.show_column_totals"
			:show-row-totals="config.show_row_totals"
		>
			<template #column-header="{ column }">
				<ChartBuilderTableColumn :chart="chart" :column="column" />
			</template>
		</DataTable>
	</div>
</template>
