<script setup lang="ts">
import { inject } from 'vue'
import DataTable from '../components/DataTable.vue'
import { Chart } from './chart'
import ChartBuilderTableColumn from './components/ChartBuilderTableColumn.vue'

const chart = inject('chart') as Chart
</script>

<template>
	<div class="flex h-[18rem] flex-col divide-y border">
		<DataTable
			v-if="chart.doc.chart_type != 'Table'"
			class="bg-white"
			:columns="chart.dataQuery.result.columns"
			:rows="chart.dataQuery.result.formattedRows"
		>
			<template #column-header="{ column }">
				<ChartBuilderTableColumn :column="column" />
			</template>
		</DataTable>
	</div>
</template>
