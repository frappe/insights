<script setup lang="ts">
import { AlertTriangle, Maximize } from 'lucide-vue-next'
import { computed, inject, ref, provide } from 'vue'
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
			}
		)
	})
}

const showExpandedChartDialog = ref(false)

const router = useRouter()
const workbook = inject(workbookKey, null)
wheneverChanges(
	() => dashboard.isEditingItem(props.item),
	(editing: boolean) => {
		if (!workbook) return
		if (editing) {
			router.push(`/workbook/${workbook.doc.name}/chart/${props.item.chart}`)
		}
	}
)
</script>

<template>
	<ChartRenderer v-if="chart" :chart="chart" />

	<div v-else class="flex h-full flex-1 flex-col items-center justify-center rounded border">
		<AlertTriangle class="h-8 w-8 text-gray-500" stroke-width="1" />
		<p class="text-p-base text-gray-500">Chart not found</p>
	</div>

	<div
		v-if="chart && chart.doc.chart_type !== 'Number'"
		class="absolute top-1.5 right-1.5 p-2 opacity-0 transition-opacity group-hover:opacity-100"
	>
		<Button variant="ghost" class="!h-7 !w-7" @click="showExpandedChartDialog = true">
			<Maximize class="h-3.5 w-3.5 text-gray-700" stroke-width="1.5" />
		</Button>
	</div>

	<Dialog
		v-if="chart"
		v-model="showExpandedChartDialog"
		:options="{
			size: '6xl',
		}"
	>
		<template #body>
			<div class="h-[75vh] w-full">
				<ChartRenderer v-if="chart" :chart="chart" />
			</div>
		</template>
	</Dialog>
</template>
