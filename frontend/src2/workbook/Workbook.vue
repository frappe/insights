<script setup lang="ts">
import { useMagicKeys, whenever } from '@vueuse/core'
import { Alert, PageHeaderBackButton, PageHeaderMobile } from 'frappe-ui'
import { AlertOctagon } from 'lucide-vue-next'
import { computed, provide, watch, watchEffect } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import LoadFailure from '../components/LoadFailure.vue'
import LoadingOverlay from '../components/LoadingOverlay.vue'
import { useIsMobile } from '../composables/useIsMobile'
import { waitUntil } from '../helpers'
import { __ } from '../translation'
import useWorkbook from './workbook'
import { workbookKey } from './workbook_key'
import WorkbookNavbar from './WorkbookNavbar.vue'
import WorkbookSidebar from './WorkbookSidebar.vue'
import useChart from '../charts/chart'
import { invalidateChart } from '../charts/chart_view'
import useDashboard from '../dashboard/dashboard'

defineOptions({ inheritAttrs: false })

const props = defineProps<{ workbook_name: string }>()

const workbook = useWorkbook(props.workbook_name)
provide(workbookKey, workbook)
window.workbook = workbook

const router = useRouter()
const route = useRoute()

// A phone reads a workbook and does not edit it: the workbook is a list of its
// items, and a tapped item opens alone at the full width
const isMobile = useIsMobile()
const isItemOpen = computed(() => route.name !== 'Workbook')
const openItemTitle = computed(() => {
	const { query_name, chart_name, dashboard_name } = route.params
	const items = [...workbook.doc.queries, ...workbook.doc.charts, ...workbook.doc.dashboards]
	const name = query_name || chart_name || dashboard_name
	return items.find((item) => item.name === name)?.title
})

waitUntil(() => !workbook.pending).then(() => {
	if (isMobile.value) return
	if (workbook.doc.queries.length === 0) {
		workbook.addQuery()
	}
	if (route.name === 'Workbook' && workbook.doc.queries.length) {
		const query = workbook.doc.queries[0]
		router.replace(`/workbook/${workbook.doc.name}/query/${query.name}`)
	}
})

// a phone opens a workbook's dashboard in the reader's view, from a link too
watchEffect(() => {
	if (isMobile.value && route.name === 'WorkbookDashboard') {
		router.replace(`/dashboards/${route.params.dashboard_name}`)
	}
})

// when we navigate from query to chart of the same query, refresh the chart
watch(
	() => ({ name: route.name, params: route.params }),
	(newRoute, oldRoute) => {
		if (newRoute.name === 'WorkbookChart' && oldRoute.name === 'WorkbookQuery') {
			const chart = useChart(newRoute.params.chart_name as string)
			// every read of the chart, not only its own: a dashboard beside it
			// renders the same chart, and its read asks the same question it
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
	document.title = workbook.loadFailure
		? __('Workbook | Insights')
		: `${workbook.doc.title} | Workbook`
})

const loadFailureTitle = computed(
	() =>
		({
			notFound: __('Workbook not found'),
			noAccess: __("You don't have access to this workbook"),
			failed: __('Could not load the workbook. Refresh to try again.'),
		})[workbook.loadFailure!],
)
</script>

<template>
	<div v-if="workbook.loadFailure" class="flex h-full w-full">
		<LoadFailure :title="loadFailureTitle">
			<Button class="mt-2" :label="__('Go to Workbooks')" :route="{ path: '/workbook' }" />
		</LoadFailure>
	</div>
	<div v-else class="flex h-full w-full flex-col">
		<LoadingOverlay v-if="workbook.pending" />
		<WorkbookNavbar class="max-sm:hidden" />
		<PageHeaderMobile
			class="flex-shrink-0 sm:hidden"
			:title="(isItemOpen ? openItemTitle : workbook.doc.title) || ''"
		>
			<template #prefix>
				<PageHeaderBackButton
					:label="__('Back')"
					:fallback-route="isItemOpen ? `/workbook/${workbook.doc.name}` : '/workbook'"
				/>
			</template>
		</PageHeaderMobile>
		<div
			class="relative flex w-full flex-1 overflow-hidden max-sm:flex-col"
			:class="workbook.showSidebar ? 'flex-row' : 'flex-col'"
		>
			<Alert
				v-if="!isItemOpen"
				class="m-3 sm:hidden"
				:title="__('Editing works on a wider screen')"
				:description="__('Here you can open its dashboards, charts and queries.')"
			/>
			<WorkbookSidebar
				:class="isItemOpen ? 'max-sm:hidden' : 'max-sm:min-h-0 max-sm:w-full max-sm:flex-1'"
			/>
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
