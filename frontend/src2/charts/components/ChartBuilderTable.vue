<script setup lang="ts">
import { inject } from 'vue'
import DataTable from '../../components/DataTable.vue'
import { Chart } from '../chart'
import ChartBuilderTableColumn from './ChartBuilderTableColumn.vue'

const chart = inject('chart') as Chart
</script>

<template>
	<div v-if="chart.doc.chart_type != 'Table'" class="flex h-[18rem] flex-col divide-y border">
		<DataTable
			class="bg-white"
			:columns="chart.dataQuery.result.columns"
			:rows="chart.dataQuery.result.formattedRows"
		>
			<template #column-header="{ column }">
				<ChartBuilderTableColumn :chart="chart" :column="column" />
			</template>
		</DataTable>
	</div>
</template>
