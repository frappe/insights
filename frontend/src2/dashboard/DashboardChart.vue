<script setup lang="ts">
import { Button } from 'frappe-ui'
import { AlertTriangle, Maximize, XIcon } from 'lucide-vue-next'
import { computed, inject, provide, ref } from 'vue'
import { useRouter } from 'vue-router'
import useChart from '../charts/chart'
import ChartRenderer from '../charts/components/ChartRenderer.vue'
import { waitUntil, wheneverChanges } from '../helpers'
import { WorkbookDashboardChart } from '../types/workbook.types'
import { workbookKey } from '../workbook/workbook'
import { Dashboard } from './dashboard'

const props = defineProps<{ item: WorkbookDashboardChart }>()
const dashboard = inject<Dashboard>('dashboard')!

const chart = computed(() => {
	if (!props.item.chart) return null
	return useChart(props.item.chart)
})

if (props.item.chart) {
	provide('chartName', props.item.chart)

	waitUntil(() => Boolean(chart.value?.isloaded)).then(() => {
		if (!chart.value?.dataQuery.result.executedSQL) {
			dashboard.refreshChart(props.item.chart)
		}

		wheneverChanges(
			() => chart.value?.doc.config.order_by,
			() => dashboard.refreshChart(props.item.chart),
			{
				deep: true,
				debounce: 500,
			},
		)
	})
}

const router = useRouter()
const workbook = inject(workbookKey, null)
wheneverChanges(
	() => dashboard.isEditingItem(props.item),
	(editing: boolean) => {
		if (!workbook) return
		if (editing) {
			router.push(`/workbook/${workbook.doc.name}/chart/${props.item.chart}`)
		}
	},
)
</script>

<template>
	<ChartRenderer v-if="chart" :chart="chart" />

	<div v-else class="flex h-full flex-1 flex-col items-center justify-center rounded border">
		<AlertTriangle class="h-8 w-8 text-gray-500" stroke-width="1" />
		<p class="text-p-base text-gray-500">Chart not found</p>
	</div>
</template>
