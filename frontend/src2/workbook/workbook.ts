import { safeJSONParse } from '@/utils'
import { watchOnce } from '@vueuse/core'
import { InjectionKey, computed, reactive, ref, toRefs } from 'vue'
import { useRouter } from 'vue-router'
import useChart from '../charts/chart'
import { ChartConfig, ChartType } from '../charts/helpers'
import useDashboard from '../dashboard/dashboard'
import { getUniqueId } from '../helpers'
import useDocumentResource from '../helpers/resource'
import { createToast } from '../helpers/toasts'
import useQuery from '../query/query'

export default function useWorkbook(name: string) {
	const workbook = getWorkbookResource(name)

	const router = useRouter()
	workbook.onAfterInsert(() => router.replace(`/workbook/${workbook.doc.name}`))
	workbook.onAfterSave(() => createToast({ title: 'Saved', variant: 'success' }))

	watchOnce(
		() => workbook.doc.name,
		() => {
			// load & cache queries, charts and dashboards
			workbook.doc.queries.forEach((query) => useQuery(query))
			workbook.doc.charts.forEach((chart) => useChart(chart))
			workbook.doc.dashboards.forEach((dashboard) => useDashboard(dashboard))

			// set first tab as active
			if (workbook.doc.queries.length) {
				setActiveTab('query', 0)
			}
		}
	)

	type ActiveTabType = 'query' | 'chart' | 'dashboard' | ''
	const activeTabType = ref<ActiveTabType>('')
	const activeTabIdx = ref(0)
	const activeQuery = computed(
		() => activeTabType.value == 'query' && workbook.doc.queries[activeTabIdx.value]
	)
	const activeChart = computed(
		() => activeTabType.value == 'chart' && workbook.doc.charts[activeTabIdx.value]
	)
	const activeDashboard = computed(
		() => activeTabType.value == 'dashboard' && workbook.doc.dashboards[activeTabIdx.value]
	)

	function setActiveTab(type: ActiveTabType, idx: number) {
		activeTabType.value = type
		activeTabIdx.value = idx
	}
	function isActiveTab(type: ActiveTabType, idx: number) {
		return activeTabType.value === type && activeTabIdx.value === idx
	}

	function addQuery() {
		const idx = workbook.doc.queries.length
		workbook.doc.queries.push({
			name: getUniqueId(),
			title: `Query ${idx + 1}`,
			operations: [],
		})
		setActiveTab('query', idx)
	}

	function removeQuery(queryName: string) {
		const idx = workbook.doc.queries.findIndex((row) => row.name === queryName)
		if (idx === -1) return
		workbook.doc.queries.splice(idx, 1)
		if (isActiveTab('query', idx)) {
			setActiveTab('', 0)
		}
	}

	function addChart() {
		const idx = workbook.doc.charts.length
		workbook.doc.charts.push({
			name: getUniqueId(),
			title: `Chart ${idx + 1}`,
			query: '',
			chart_type: 'Line',
			config: {} as ChartConfig,
		})
		setActiveTab('chart', idx)
	}

	function removeChart(chartName: string) {
		const idx = workbook.doc.charts.findIndex((row) => row.name === chartName)
		if (idx === -1) return
		workbook.doc.charts.splice(idx, 1)
		if (isActiveTab('chart', idx)) {
			setActiveTab('', 0)
		}
	}

	function addDashboard() {
		const idx = workbook.doc.dashboards.length
		workbook.doc.dashboards.push({
			name: getUniqueId(),
			title: `Dashboard ${idx + 1}`,
			items: [],
		})
		setActiveTab('dashboard', idx)
	}

	function removeDashboard(dashboardName: string) {
		const idx = workbook.doc.dashboards.findIndex((row) => row.name === dashboardName)
		if (idx === -1) return
		workbook.doc.dashboards.splice(idx, 1)
		if (isActiveTab('dashboard', idx)) {
			setActiveTab('', 0)
		}
	}

	return reactive({
		...toRefs(workbook),

		activeTabType,
		activeTabIdx,
		activeQuery,
		activeChart,
		activeDashboard,
		setActiveTab,
		isActiveTab,

		addQuery,
		removeQuery,
		addChart,
		removeChart,
		addDashboard,
		removeDashboard,
	})
}

export type Workbook = ReturnType<typeof useWorkbook>
export const workbookKey = Symbol() as InjectionKey<Workbook>

function getWorkbookResource(name: string) {
	const doctype = 'Insights Workbook'
	const workbook = useDocumentResource<InsightsWorkbook>(doctype, name, {
		initialDoc: {
			doctype,
			name: '',
			title: '',
			queries: [],
			charts: [],
			dashboards: [],
		},
		transform(doc) {
			doc.queries = safeJSONParse(doc.queries) || []
			doc.charts = safeJSONParse(doc.charts) || []
			doc.dashboards = safeJSONParse(doc.dashboards) || []
			return doc
		},
	})
	return workbook
}

type InsightsWorkbook = {
	doctype: 'Insights Workbook'
	name: string
	title: string
	queries: WorkbookQuery[]
	charts: WorkbookChart[]
	dashboards: WorkbookDashboard[]
}

export type WorkbookQuery = {
	name: string
	title: string
	operations: Operation[]
}

export type WorkbookChart = {
	name: string
	title: string
	query: string
	chart_type: ChartType
	config: ChartConfig
}

export type WorkbookDashboard = {
	name: string
	title: string
	items: WorkbookDashboardItem[]
}
export type WorkbookDashboardItem =
	| WorkbookDashboardChart
	| WorkbookDashboardFilter
	| WorkbookDashboardText
export type Layout = {
	i: string
	x: number
	y: number
	w: number
	h: number
}
export type WorkbookDashboardChart = {
	type: 'chart'
	chart: string
	layout: Layout
}
export type WorkbookDashboardFilter = {
	type: 'filter'
	column: DashboardFilterColumn
	layout: Layout
}
export type WorkbookDashboardText = {
	type: 'text'
	text: string
	layout: Layout
}
export type DashboardFilterColumn = {
	query: string
	name: string
	type: ColumnDataType
}
