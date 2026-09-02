<script setup lang="ts">
import { AlertTriangle } from 'lucide-vue-next'
import { computed, inject, provide } from 'vue'
import { useRouter } from 'vue-router'
import useChart from '../charts/chart'
import ChartCardFrame from '../charts/components/ChartCardFrame.vue'
import ChartRenderer from '../charts/components/ChartRenderer.vue'
import { waitUntil, wheneverChanges } from '../helpers'
import { WorkbookDashboardChart } from '../types/workbook.types'
import { workbookKey } from '../workbook/workbook_key'
import { Dashboard } from './dashboard'

const props = defineProps<{ item: WorkbookDashboardChart }>()
const dashboard = inject<Dashboard>('dashboard')!

const chart = computed(() => {
	if (!props.item.chart) return null
	return useChart(props.item.chart)
})
// the card, drawn from the config being edited rather than from the saved
// chart, so an unsaved edit shows here too. A public link reads the saved chart.
const read = computed(() => (props.item.chart ? dashboard.chartRead(props.item.chart) : null))

if (props.item.chart) {
	provide('chartName', props.item.chart)

	waitUntil(() => Boolean(chart.value?.isloaded)).then(() => {
		if (!read.value?.result.executedSQL) {
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
	<!-- a public link draws the card read-only: sorting is a query, and a drill
	     needs an authoring seat, so neither is offered there -->
	<ChartCardFrame v-if="read && dashboard.shared" :chart="read" readonly />
	<ChartRenderer v-else-if="read" :chart="read" />

	<!-- not one of the card's states: a grid item that names no chart has no store
	     to be loading, failed or empty. It is the layout that is wrong, not a read. -->
	<div
		v-else
		class="flex h-full flex-1 flex-col items-center justify-center rounded-4 border border-outline-gray-2"
	>
		<AlertTriangle class="h-8 w-8 text-ink-gray-4" stroke-width="1" />
		<p class="text-p-base text-ink-gray-4">Chart not found</p>
	</div>
</template>
