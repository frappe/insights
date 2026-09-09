<script setup lang="ts">
import { Button, Tooltip } from 'frappe-ui'
import { AlertTriangle, Pencil } from 'lucide-vue-next'
import { computed, inject, provide } from 'vue'
import { useRouter } from 'vue-router'
import useChart from '../charts/chart'
import ChartCardFrame from '../charts/components/ChartCardFrame.vue'
import ChartRenderer from '../charts/components/ChartRenderer.vue'
import { waitUntil, wheneverChanges } from '../helpers'
import { __ } from '../translation'
import { WorkbookDashboardChart } from '../types/workbook.types'
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

// Editing a chart is not editing the dashboard. The chart is a workbook object
// and the dashboard only names it, so the action sits on the card in view mode
// and never touches the layout state.
const router = useRouter()
const canEditChart = computed(() => Boolean(props.item.chart) && dashboard.doc.has_workbook_access)
function editChart() {
	router.push(`/workbook/${dashboard.doc.workbook}/chart/${props.item.chart}`)
}
</script>

<template>
	<!-- a public link draws the card read-only: sorting is a query, and a drill
	     needs an authoring seat, so neither is offered there -->
	<ChartCardFrame v-if="read && dashboard.shared" :chart="read" readonly />
	<ChartRenderer v-else-if="read" :chart="read">
		<template v-if="canEditChart" #actions>
			<Tooltip :text="__('Edit Chart')">
				<Button variant="ghost" @click="editChart()">
					<Pencil class="h-3.5 w-3.5 text-ink-gray-6" stroke-width="1.5" />
				</Button>
			</Tooltip>
		</template>
	</ChartRenderer>

	<!-- not one of the card's states: a grid item that names no chart has no store
	     to be loading, failed or empty. It is the layout that is wrong, not a read. -->
	<div
		v-else
		class="flex h-full flex-1 flex-col items-center justify-center rounded-4 border border-outline-gray-2"
	>
		<div class="flex items-center gap-1.5 text-p-base text-ink-gray-4">
			<AlertTriangle class="h-3.5 w-3.5 shrink-0 text-ink-red-5" stroke-width="1.5" />
			<span>Chart not found</span>
		</div>
	</div>
</template>
