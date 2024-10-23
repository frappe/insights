<script setup lang="ts">
import { inject, ref } from 'vue'
import DataTable from '../../components/DataTable.vue'
import { QueryResultColumn, QueryResultRow } from '../../types/query.types'
import { Chart } from '../chart'
import ChartBuilderTableColumn from './ChartBuilderTableColumn.vue'
import DrillDown from './DrillDown.vue'

const chart = inject('chart') as Chart

const drillOn = ref<{ row: QueryResultRow; column: QueryResultColumn } | null>(null)
</script>

<template>
	<div v-if="chart.doc.chart_type != 'Table'" class="flex h-[18rem] flex-col divide-y border">
		<DataTable
			class="bg-white"
			:columns="chart.dataQuery.result.columns"
			:rows="chart.dataQuery.result.formattedRows"
			@cell-dbl-click="(row, column) => (drillOn = { row, column })"
		>
			<template #column-header="{ column }">
				<ChartBuilderTableColumn :chart="chart" :column="column" />
			</template>
		</DataTable>

		<DrillDown v-if="drillOn" :chart="chart" :row="drillOn.row" :column="drillOn.column" />
	</div>
</template>
