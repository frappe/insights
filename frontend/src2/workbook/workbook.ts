import { call } from 'frappe-ui'
import { computed, InjectionKey, reactive, toRefs } from 'vue'
import { useRouter } from 'vue-router'
import useChart from '../charts/chart'
import useDashboard from '../dashboard/dashboard'
import { getUniqueId, safeJSONParse, wheneverChanges } from '../helpers'
import { confirmDialog } from '../helpers/confirm_dialog'
import useDocumentResource from '../helpers/resource'
import { createToast } from '../helpers/toasts'
import useQuery, { getCachedQuery } from '../query/query'
import session from '../session'
import { Join, Source } from '../types/query.types'
import type {
	InsightsWorkbook,
	WorkbookChart,
	WorkbookSharePermission,
} from '../types/workbook.types'
import { handleOldYAxisConfig } from '../charts/helpers'

export default function useWorkbook(name: string) {
	const workbook = getWorkbookResource(name)

	const router = useRouter()
	workbook.onAfterInsert(() => {
		window.location.href = window.location.href.replace(name, workbook.doc.name)
	})
	workbook.onAfterSave(() => createToast({ title: 'Saved', variant: 'success' }))

	wheneverChanges(
		() => workbook.doc,
		() => {
			// load & cache queries, charts and dashboards

			// fix: dicarding workbook changes doesn't reset the query/chart/dashboard doc
			// this is because, when the workbook doc is updated,
			// the reference to the workbook.doc.queries/charts/dashboards is lost
			// so we need to update the references to the new queries/charts/dashboards
			workbook.doc.queries.forEach((q) => (useQuery(q).doc = q))
			workbook.doc.charts.forEach((c) => (useChart(c).doc = c))
			workbook.doc.dashboards.forEach((d) => (useDashboard(d).doc = d))
		}
	)

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
			use_live_connection: true,
			operations: [],
		})
		setActiveTab('query', idx)
	}

	function removeQuery(queryName: string) {
		function _remove() {
			const idx = workbook.doc.queries.findIndex((row) => row.name === queryName)
			if (idx === -1) return
			workbook.doc.queries.splice(idx, 1)
			if (isActiveTab('query', idx)) {
				setActiveTab('', 0)
			}
		}

		confirmDialog({
			title: 'Delete Query',
			message: 'Are you sure you want to delete this query?',
			onSuccess: _remove,
		})
	}

	function addChart() {
		const idx = workbook.doc.charts.length
		workbook.doc.charts.push({
			name: getUniqueId(),
			title: `Chart ${idx + 1}`,
			query: '',
			chart_type: 'Line',
			public: false,
			config: {} as WorkbookChart['config'],
		})
		setActiveTab('chart', idx)
	}

	function removeChart(chartName: string) {
		function _remove() {
			const idx = workbook.doc.charts.findIndex((row) => row.name === chartName)
			if (idx === -1) return
			workbook.doc.charts.splice(idx, 1)
			if (isActiveTab('chart', idx)) {
				setActiveTab('', 0)
			}
		}

		confirmDialog({
			title: 'Delete Chart',
			message: 'Are you sure you want to delete this chart?',
			onSuccess: _remove,
		})
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
		function _remove() {
			const idx = workbook.doc.dashboards.findIndex((row) => row.name === dashboardName)
			if (idx === -1) return
			workbook.doc.dashboards.splice(idx, 1)
			if (isActiveTab('dashboard', idx)) {
				setActiveTab('', 0)
			}
		}

		confirmDialog({
			title: 'Delete Dashboard',
			message: 'Are you sure you want to delete this dashboard?',
			onSuccess: _remove,
		})
	}

	const isOwner = computed(() => workbook.doc.owner === session.user?.email)
	const canShare = computed(() => isOwner.value)

	async function getSharePermissions(): Promise<WorkbookSharePermission[]> {
		const method = 'insights.api.workbooks.get_share_permissions'
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
		const method = 'insights.api.workbooks.update_share_permissions'
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

	function deleteWorkbook() {
		confirmDialog({
			title: 'Delete Workbook',
			message: 'Are you sure you want to delete this workbook?',
			theme: 'red',
			onSuccess: () => {
				workbook.delete().then(() => {
					router.replace('/workbook')
				})
			},
		})
	}

	function getLinkedQueries(query_name: string): string[] {
		const query = getCachedQuery(query_name)
		if (!query) {
			console.error(`Query ${query_name} not found`)
			return []
		}

		const querySource = query.doc.operations.find(
			(op) => op.type === 'source' && op.table.type === 'query' && op.table.query_name
		) as Source

		const queryJoins = query.doc.operations.filter(
			(op) => op.type === 'join' && op.table.type === 'query' && op.table.query_name
		) as Join[]

		const linkedQueries = [] as string[]
		if (querySource && querySource.table.type === 'query') {
			linkedQueries.push(querySource.table.query_name)
		}
		if (queryJoins.length) {
			queryJoins.forEach((j) => {
				if (j.table.type === 'query') {
					linkedQueries.push(j.table.query_name)
				}
			})
		}

		const linkedQueriesByQuery = {} as Record<string, string[]>
		linkedQueries.forEach((q) => {
			linkedQueriesByQuery[q] = getLinkedQueries(q)
		})

		Object.values(linkedQueriesByQuery).forEach((subLinkedQueries) => {
			linkedQueries.concat(subLinkedQueries)
		})

		return linkedQueries
	}

	return reactive({
		...toRefs(workbook),
		canShare,
		isOwner,

		showSidebar: true,

		isActiveTab,

		addQuery,
		removeQuery,

		addChart,
		removeChart,

		addDashboard,
		removeDashboard,

		getSharePermissions,
		updateSharePermissions,

		getLinkedQueries,

		delete: deleteWorkbook,
	})
}

export type Workbook = ReturnType<typeof useWorkbook>
export const workbookKey = Symbol() as InjectionKey<Workbook>

function getWorkbookResource(name: string) {
	const doctype = 'Insights Workbook'
	const workbook = useDocumentResource<InsightsWorkbook>(doctype, name, {
		initialDoc: {
			doctype,
			name,
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
				chart.config.filters = chart.config.filters?.filters?.length
					? chart.config.filters
					: {
							filters: [],
							logical_operator: 'And',
					  }
				chart.config.order_by = chart.config.order_by || []
				chart.config.limit = 100

				if ('y_axis' in chart.config && Array.isArray(chart.config.y_axis)) {
					// @ts-ignore
					chart.config.y_axis = handleOldYAxisConfig(chart.config.y_axis)
				}
			})
			return doc
		},
	})
	return workbook
}
