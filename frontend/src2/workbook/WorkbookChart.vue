<script setup lang="ts">
import { inject, ref } from 'vue'
import ChartBuilder from '../charts/ChartBuilder.vue'
import useChart from '../charts/chart'
import { workbookKey } from './workbook'
import { mirrorTitleToWorkbook } from './workbook_items'
import { useRouter } from 'vue-router'

const props = defineProps<{ workbook_name?: string; chart_name: string }>()

const router = useRouter()
const workbook = inject(workbookKey)!

let chart_name = ref(props.chart_name)
const index = Number(props.chart_name)
if (
	index >= 0 &&
	workbook.doc.charts[index] &&
	!workbook.doc.charts.find((q) => q.name === props.chart_name)
) {
	chart_name.value = workbook.doc.charts[index].name
	router.replace(`/workbook/${workbook.doc.name}/chart/${chart_name.value}`)
}

mirrorTitleToWorkbook(useChart(chart_name.value), 'chart')
</script>

<template>
	<ChartBuilder
		:chart_name="chart_name"
		:queries="
			workbook.doc.queries.map((q) => {
				return { label: q.title, value: q.name }
			})
		"
	/>
</template>
