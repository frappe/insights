<script setup lang="ts">
import { useMagicKeys, whenever } from '@vueuse/core'
import { AlertOctagon } from 'lucide-vue-next'
import { provide, watch, watchEffect } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import LoadingOverlay from '../components/LoadingOverlay.vue'
import { waitUntil } from '../helpers'
import useWorkbook from './workbook'
import { workbookKey } from './workbook_key'
import WorkbookNavbar from './WorkbookNavbar.vue'
import WorkbookSidebar from './WorkbookSidebar.vue'
import useChart from '../charts/chart'
import { invalidateChart } from '../charts/chart_read'
import useDashboard from '../dashboard/dashboard'

defineOptions({ inheritAttrs: false })

const props = defineProps<{ workbook_name: string }>()

const workbook = useWorkbook(props.workbook_name)
provide(workbookKey, workbook)
window.workbook = workbook

const router = useRouter()
const route = useRoute()

// the workbook opens on a query, and an empty one gets its first
waitUntil(() => !workbook.pending).then(() => {
	if (workbook.doc.queries.length === 0) {
		workbook.addQuery()
	}
	if (route.name === 'Workbook' && workbook.doc.queries.length) {
		const query = workbook.doc.queries[0]
		router.replace(`/workbook/${workbook.doc.name}/query/${query.name}`)
	}
})

// when we navigate from query to chart of the same query, refresh the chart
watch(
	() => ({ name: route.name, params: route.params }),
	(newRoute, oldRoute) => {
		if (newRoute.name === 'WorkbookChart' && oldRoute.name === 'WorkbookQuery') {
			const chart = useChart(newRoute.params.chart_name as string)
			// every read of the chart, not only its own: a dashboard beside it
			// draws the same chart, and its read asks the same question it
			// asked before the query changed under it
			if (chart.doc.query === oldRoute.params.query_name) {
				invalidateChart(String(chart.doc.name))
			}
		}
	},
)

const keys = useMagicKeys()
const cmdS = keys['Meta+S']
whenever(cmdS, () => workbook.save())

const cmdV = keys['Meta+V']
whenever(cmdV, () => {
	if (!navigator.clipboard) {
		return
	}
	navigator.clipboard.readText().then((text) => {
		try {
			const json = JSON.parse(text)
			if (json.type === 'Query') {
				workbook.importQuery(json)
			} else if (json.type === 'Chart') {
				workbook.importChart(json)
			}
		} catch (e) {
			console.error(e)
		}
	})
})

watchEffect(() => {
	document.title = `${workbook.doc.title} | Workbook`
})
</script>

<template>
	<div class="flex h-full w-full flex-col">
		<LoadingOverlay v-if="workbook.pending" />
		<WorkbookNavbar />
		<div
			class="relative flex w-full flex-1 overflow-hidden"
			:class="workbook.showSidebar ? 'flex-row' : 'flex-col'"
		>
			<WorkbookSidebar />
			<RouterView v-if="!workbook.pending" :key="route.fullPath" v-slot="{ Component }">
				<component :is="Component" />
				<div v-if="false" class="flex flex-1 items-center justify-center">
					<div class="flex flex-col items-center gap-4">
						<AlertOctagon class="h-16 w-16 text-ink-gray-3" stroke-width="1" />
						<p
							v-if="workbook.doc.queries.length"
							class="text-center text-lg leading-4 text-ink-gray-4"
						>
							This tab doesn't exist <br />
							Try switching to another tab
						</p>
						<p v-else class="text-center text-lg leading-5 text-ink-gray-4">
							You haven't added any queries yet <br />
							Click on the "+" button to add a new query
						</p>
					</div>
				</div>
			</RouterView>
		</div>
	</div>
</template>
