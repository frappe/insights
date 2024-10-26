<script setup lang="ts">
import { call } from 'frappe-ui'
import { reactive } from 'vue'
import { QueryResult } from '../types/query.types'
import { WorkbookChart } from '../types/workbook.types'
import ChartRenderer from './components/ChartRenderer.vue'

const props = defineProps<{ chart_name: string }>()

const chart = reactive({
	doc: {} as WorkbookChart,
	result: {} as QueryResult,
})

call('insights.api.workbooks.fetch_shared_chart_data', { chart_name: props.chart_name }).then(
	(res: any) => {
		chart.doc = res.chart
		chart.result = res.results
	}
)
</script>

<template>
	<div class="h-full w-full">
		<ChartRenderer
			v-if="chart.doc.name"
			:title="chart.doc.title"
			:chart_type="chart.doc.chart_type"
			:config="chart.doc.config"
			:operations="chart.doc.operations"
			:result="chart.result"
		/>
	</div>
</template>
