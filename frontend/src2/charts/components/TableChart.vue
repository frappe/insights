<script setup lang="ts">
import { computed } from 'vue'
import DataTable from '../../components/DataTable.vue'
import { TableChartConfig } from '../../types/chart.types'
import { QueryResult } from '../../types/query.types'
import { WorkbookChart } from '../../types/workbook.types'
import ChartBuilderTableColumn from './ChartBuilderTableColumn.vue'
import ChartTitle from './ChartTitle.vue'

const props = defineProps<{
	title: string
	config: WorkbookChart['config']
	result: QueryResult
}>()

const tableConfig = computed(() => props.config as TableChartConfig)
</script>

<template>
	<div class="flex h-full w-full flex-col overflow-hidden rounded bg-white shadow">
		<ChartTitle v-if="props.title" :title="props.title" />
		<DataTable
			class="w-full flex-1 overflow-hidden border-t"
			:columns="props.result.columns"
			:rows="props.result.formattedRows"
			:show-filter-row="tableConfig.show_filter_row"
			:show-column-totals="tableConfig.show_column_totals"
			:show-row-totals="tableConfig.show_row_totals"
		>
			<template #column-header="{ column }">
				<ChartBuilderTableColumn :config="props.config" :column="column" />
			</template>
		</DataTable>
	</div>
</template>
