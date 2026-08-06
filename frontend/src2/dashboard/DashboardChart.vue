<script setup lang="ts">
import { Button } from 'frappe-ui'
import { AlertTriangle, Maximize, XIcon } from 'lucide-vue-next'
import { computed, inject, provide, watch } from 'vue'
import useChart from '../charts/chart'
import useChartPreview from '../charts/chart_preview'
import ChartRenderer from '../charts/components/ChartRenderer.vue'
import { waitUntil, wheneverChanges } from '../helpers'
import { navigate } from '../helpers/navigation'
import { WorkbookDashboardChart } from '../types/workbook.types'
import { workbookKey } from '../workbook/workbook_key'
import { Dashboard } from './dashboard'

const props = defineProps<{ item: WorkbookDashboardChart; refreshToken?: number }>()
const emit = defineEmits<{ loaded: [executedAt: Date] }>()
const dashboard = inject<Dashboard>('dashboard')!

const chart = computed(() => {
	if (!props.item.chart) return null
	return useChart(props.item.chart)
})
// the builder's own card, drawn from the config being edited rather than from
// the saved chart, so an unsaved edit shows here too
const preview = computed(() => (chart.value ? useChartPreview(chart.value) : null))

if (props.item.chart) {
	provide('chartName', props.item.chart)

	waitUntil(() => Boolean(chart.value?.isloaded)).then(() => {
		if (!preview.value?.result.executedSQL) {
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

// the page's one refresh, on the card that knows what to re-run
watch(
	() => props.refreshToken,
	() => props.item.chart && dashboard.refreshChart(props.item.chart, true),
)

// when these rows were produced. The page's freshness stamp is the oldest of
// its cards, so every card says.
watch(
	() => preview.value?.executedAt,
	(executedAt) => executedAt && emit('loaded', executedAt),
)

const workbook = inject(workbookKey, null)
wheneverChanges(
	() => dashboard.isEditingItem(props.item),
	(editing: boolean) => {
		if (!workbook) return
		if (editing) {
			navigate(`/workbook/${workbook.doc.name}/chart/${props.item.chart}`)
		}
	},
)
</script>

<template>
	<ChartRenderer v-if="preview" :chart="preview" />

	<div v-else class="flex h-full flex-1 flex-col items-center justify-center rounded border">
		<AlertTriangle class="h-8 w-8 text-ink-gray-4" stroke-width="1" />
		<p class="text-p-base text-ink-gray-4">Chart not found</p>
	</div>
</template>
