import { safeJSONParse } from '@/utils'
import { call } from 'frappe-ui'
import { computed, InjectionKey, reactive, toRefs } from 'vue'
import { useRouter } from 'vue-router'
import useChart from '../charts/chart'
import { ChartConfig, ChartType } from '../charts/helpers'
import useDashboard from '../dashboard/dashboard'
import { getUniqueId } from '../helpers'
import useDocumentResource from '../helpers/resource'
import { createToast } from '../helpers/toasts'
import useQuery from '../query/query'
import session from '../session'

export default function useWorkbook(name: string) {
	const workbook = getWorkbookResource(name)

	const router = useRouter()
	workbook.onAfterInsert(() => router.replace(`/workbook/${workbook.doc.name}`))
	workbook.onAfterSave(() => createToast({ title: 'Saved', variant: 'success' }))
	workbook.onAfterLoad((doc: InsightsWorkbook) => {
		// load & cache queries, charts and dashboards

		// fix: dicarding workbook changes doesn't reset the query/chart/dashboard doc
		// this is because, when the workbook doc is updated,
		// the reference to the workbook.doc.queries/charts/dashboards is lost
		// so we need to update the references to the new queries/charts/dashboards
		doc.queries.forEach((q) => (useQuery(q).doc = q))
		doc.charts.forEach((c) => (useChart(c).doc = c))
		doc.dashboards.forEach((d) => (useDashboard(d).doc = d))
	})

	function setActiveTab(type: 'query' | 'chart' | 'dashboard' | '', idx: number) {
		router.replace(
			type ? `/workbook/${workbook.name}/${type}/${idx}` : `/workbook/${workbook.name}`
		)
	}
	function isActiveTab(type: 'query' | 'chart' | 'dashboard', idx: number) {
		const url = router.currentRoute.value.path
		const regex = new RegExp(`/workbook/${workbook.name}/${type}/${idx}`)
		return regex.test(url)
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
			config: {} as WorkbookChart['config'],
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

	async function getSharePermissions(): Promise<WorkbookSharePermission[]> {
		const method =
			'insights.insights.doctype.insights_workbook.insights_workbook.get_share_permissions'
		return call(method, { workbook_name: workbook.name }).then((permissions: any) => {
			return permissions.map((p: any) => {
				return {
					email: p.user,
					full_name: p.full_name,
					access: p.read ? (p.write ? 'edit' : 'view') : undefined,
				}
			})
		})
	}

	async function updateSharePermissions(permissions: WorkbookSharePermission[]) {
		const method =
			'insights.insights.doctype.insights_workbook.insights_workbook.update_share_permissions'
		return call(method, {
			workbook_name: workbook.name,
			permissions: permissions.map((p) => {
				return {
					user: p.email,
					read: p.access === 'view',
					write: p.access === 'edit',
				}
			}),
		})
	}

	const canShare = computed(() => workbook.doc.owner === session.user?.email)

	return reactive({
		...toRefs(workbook),
		canShare,

		isActiveTab,

		addQuery,
		removeQuery,
		addChart,
		removeChart,
		addDashboard,
		removeDashboard,

		getSharePermissions,
		updateSharePermissions,
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
			owner: '',
			title: '',
			queries: [],
			charts: [],
			dashboards: [],
		},
		transform(doc) {
			doc.queries = safeJSONParse(doc.queries) || []
			doc.charts = safeJSONParse(doc.charts) || []
			doc.dashboards = safeJSONParse(doc.dashboards) || []
			doc.charts.forEach((chart) => {
				chart.config.order_by = chart.config.order_by || []
			})
			return doc
		},
	})
	return workbook
}

type InsightsWorkbook = {
	doctype: 'Insights Workbook'
	name: string
	owner: string
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
	config: ChartConfig & {
		order_by: OrderByArgs[]
	}
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

export type ShareAccess = 'view' | 'edit' | undefined
export type WorkbookSharePermission = { email: string; full_name: string; access: ShareAccess }
