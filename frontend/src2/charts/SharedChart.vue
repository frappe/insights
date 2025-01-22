<script setup lang="ts">
import { call } from 'frappe-ui'
import { reactive, ref } from 'vue'
import { showErrorToast } from '../helpers'
import { getFormattedRows } from '../query/helpers'
import { QueryResult } from '../types/query.types'
import { InsightsChartv3 } from '../types/workbook.types'
import ChartRenderer from './components/ChartRenderer.vue'

const props = defineProps<{ chart_name: string }>()

const chart = reactive({
	doc: {} as InsightsChartv3,
	result: {} as QueryResult,
})

const fetchingData = ref(true)
call('insights.api.workbooks.fetch_shared_chart_data', { chart_name: props.chart_name })
	.then((res: any) => {
		fetchingData.value = false
		chart.doc = res.chart
		chart.result = res.results
		chart.result.formattedRows = getFormattedRows(chart.result, chart.doc.operations)
	})
	.catch(showErrorToast)
</script>

<template>
	<div class="h-full w-full">
		<ChartRenderer
			v-if="chart.doc.name"
			:title="chart.doc.title"
			:chart_type="chart.doc.chart_type"
			:config="chart.doc.config"
			:operations="chart.doc.operations"
			:use_live_connection="Boolean(chart.doc.use_live_connection)"
			:result="chart.result"
			:loading="fetchingData"
		/>
	</div>
</template>
