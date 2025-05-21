import { call } from 'frappe-ui'
import { computed, InjectionKey, reactive, toRefs } from 'vue'
import useChart, { newChart } from '../charts/chart'
import useDashboard, { newDashboard } from '../dashboard/dashboard'
import {
	copy,
	copyToClipboard,
	getUniqueId,
	safeJSONParse,
	showErrorToast,
	waitUntil,
	wheneverChanges,
} from '../helpers'
import { confirmDialog } from '../helpers/confirm_dialog'
import useDocumentResource from '../helpers/resource'
import { createToast } from '../helpers/toasts'
import useQuery, { newQuery } from '../query/query'
import router from '../router'
import session from '../session'
import type {
	InsightsWorkbook,
	WorkbookSharePermission as WorkbookUserPermission,
} from '../types/workbook.types'

const workbooks = new Map<string, Workbook>()

export default function useWorkbook(name: string) {
	name = String(name)
	const existingWorkbook = workbooks.get(name)
	if (existingWorkbook) return existingWorkbook

	const workbook = makeWorkbook(name)
	workbooks.set(name, workbook)
	return workbook
}

function makeWorkbook(name: string) {
	const workbook = getWorkbookResource(name)

	// getLinkedQueries expects the query to be loaded
	wheneverChanges(
		() => workbook.doc.queries.map((q) => q.name),
		() => workbook.doc.queries.forEach((q) => useQuery(q.name)),
		{ deep: true }
	)

	function setActiveTab(type: 'query' | 'chart' | 'dashboard', name: string) {
		router.replace(`/workbook/${workbook.name}/${type}/${name}`)
	}
	function isActiveTab(type: 'query' | 'chart' | 'dashboard', name: string) {
		const url = router.currentRoute.value.path
		const regex = new RegExp(`/workbook/${workbook.name}/${type}/${name}`)
		return regex.test(url)
	}

	async function addQuery() {
		const query = newQuery()
		query.doc.title = 'Query ' + (workbook.doc.queries.length + 1)
		query.doc.workbook = workbook.doc.name
		query.doc.use_live_connection = true
		query.insert().then(() => {
			workbook.doc.queries.push({
				name: query.doc.name,
				title: query.doc.title,
			})
			setActiveTab('query', query.doc.name)
		})
	}

	function removeQuery(name: string) {
		function _remove() {
			const idx = workbook.doc.queries.findIndex((row) => row.name === name)
			if (idx === -1) return

			const query = useQuery(name)
			waitUntil(() => query.isloaded).then(() => query.delete())

			openNext('query', idx)
			workbook.doc.queries.splice(idx, 1)
		}

		confirmDialog({
			title: 'Delete Query',
			message: 'Are you sure you want to delete this query?',
			onSuccess: _remove,
		})
	}

	function addChart(query_name?: string) {
		const chart = newChart()
		chart.doc.title = 'Chart ' + (workbook.doc.charts.length + 1)
		chart.doc.workbook = workbook.doc.name
		chart.doc.query = query_name || ''
		chart.doc.chart_type = 'Bar'
		chart.insert().then(() => {
			workbook.doc.charts.push({
				name: chart.doc.name,
				title: chart.doc.title,
				query: chart.doc.query,
				chart_type: 'Bar',
			})
			setActiveTab('chart', chart.doc.name)
		})
	}

	function removeChart(chartName: string) {
		function _remove() {
			const idx = workbook.doc.charts.findIndex((row) => row.name === chartName)
			if (idx === -1) return

			const chart = useChart(chartName)
			waitUntil(() => chart.isloaded).then(() => chart.delete())

			openNext('chart', idx)
			workbook.doc.charts.splice(idx, 1)
		}

		confirmDialog({
			title: 'Delete Chart',
			message: 'Are you sure you want to delete this chart?',
			onSuccess: _remove,
		})
	}

	function addDashboard() {
		const dashboard = newDashboard()
		dashboard.doc.title = 'Dashboard ' + (workbook.doc.dashboards.length + 1)
		dashboard.doc.workbook = workbook.doc.name
		dashboard.insert().then(() => {
			workbook.doc.dashboards.push({
				name: dashboard.doc.name,
				title: dashboard.doc.title,
			})
			setActiveTab('dashboard', dashboard.doc.name)
		})
	}

	function removeDashboard(dashboardName: string) {
		function _remove() {
			const idx = workbook.doc.dashboards.findIndex((row) => row.name === dashboardName)
			if (idx === -1) return

			const dashboard = useDashboard(dashboardName)
			waitUntil(() => dashboard.isloaded).then(() => dashboard.delete())

			openNext('dashboard', idx)
			workbook.doc.dashboards.splice(idx, 1)
		}

		confirmDialog({
			title: 'Delete Dashboard',
			message: 'Are you sure you want to delete this dashboard?',
			onSuccess: _remove,
		})
	}

	function openNext(type: 'query' | 'chart' | 'dashboard', idx: number) {
		const items = {
			query: workbook.doc.queries,
			chart: workbook.doc.charts,
			dashboard: workbook.doc.dashboards,
		}[type]

		let nextIndex = idx + 1

		if (nextIndex >= items.length) {
			nextIndex = 0
		}
		if (nextIndex < 0) {
			nextIndex = items.length - 1
		}
		if (nextIndex >= 0 && nextIndex < items.length) {
			setActiveTab(type, items[nextIndex].name)
			return
		}

		router.replace(`/workbook/${workbook.name}`)
	}

	const isOwner = computed(() => workbook.doc.owner === session.user?.email)
	const canShare = computed(() => isOwner.value)

	async function getSharePermissions(): Promise<UpdateSharePermissionsArgs> {
		const method = 'insights.api.workbooks.get_share_permissions'
		return call(method, { workbook_name: workbook.name }).then((permissions: any) => {
			return {
				user_permissions: permissions.user_permissions.map((p: any) => {
					return {
						email: p.user,
						full_name: p.full_name,
						access: p.read ? (p.write ? 'edit' : 'view') : undefined,
					}
				}),
				organization_access: permissions.organization_access,
			}
		})
	}

	type UpdateSharePermissionsArgs = {
		user_permissions: WorkbookUserPermission[]
		organization_access?: 'view' | 'edit'
	}
	async function updateSharePermissions(args: UpdateSharePermissionsArgs) {
		const method = 'insights.api.workbooks.update_share_permissions'
		return call(method, {
			workbook_name: workbook.name,
			organization_access: args.organization_access,
			user_permissions: args.user_permissions.map((p) => {
				return {
					user: p.email,
					read: p.access === 'view',
					write: p.access === 'edit',
				}
			}),
		}).catch(showErrorToast)
	}

	function duplicate() {
		confirmDialog({
			title: 'Duplicate Workbook',
			message: 'Duplicating this workbook will create a new workbook and copy all queries, charts and dashboards to it. Do you want to continue?',
			onSuccess: () => {
				workbook.call('duplicate')
				.then((name: any) => {
					createToast({
						message: 'Workbook duplicated successfully',
						variant: 'success',
					})
					// FIX: debug why new workbook is not loaded
					router.push(`/workbook/${name}`)
				})
				.catch(showErrorToast)
			},
		})
	}

	function importQuery(query: any) {
		confirmDialog({
			title: 'Import Query',
			message: 'Are you sure you want to import this query?',
			onSuccess: () => {
				workbook.call('import_query', { query }).then((name) => {
					workbook.load().then(() => {
						createToast({
							message: 'Query imported successfully',
							variant: 'success',
						})
						setActiveTab('query', name)
					})
				})
			},
		})
	}

	function importChart(chart: any) {
		confirmDialog({
			title: 'Import Chart',
			message: 'Are you sure you want to import this chart?',
			onSuccess: () => {
				workbook.call('import_chart', { chart }).then((name) => {
					workbook.load().then(() => {
						createToast({
							message: 'Chart imported successfully',
							variant: 'success',
						})
						setActiveTab('chart', name)
					})
				})
			},
		})
	}

	function copyJSON() {
		workbook.call('export').then(data => {
			copyToClipboard(JSON.stringify(data, null, 2))
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

	return reactive({
		...toRefs(workbook),
		canShare,
		isOwner,

		showSidebar: true,

		isActiveTab,

		duplicate,
		importQuery,
		importChart,


		addQuery,
		removeQuery,

		addChart,
		removeChart,

		addDashboard,
		removeDashboard,

		getSharePermissions,
		updateSharePermissions,

		getLinkedQueries,

		copy: copyJSON,

		delete: deleteWorkbook,
	})
}

export type Workbook = ReturnType<typeof makeWorkbook>
export const workbookKey = Symbol() as InjectionKey<Workbook>

export function getWorkbookResource(name: string) {
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
			read_only: false,
		},
		enableAutoSave: true,
		disableLocalStorage: true,
		transform(doc: any) {
			doc.queries = safeJSONParse(doc.queries) || []
			doc.charts = safeJSONParse(doc.charts) || []
			doc.dashboards = safeJSONParse(doc.dashboards) || []
			return doc
		},
	})

	workbook.onAfterLoad(() => workbook.call('track_view').catch(() => {}))
	wheneverChanges(() => workbook.doc.read_only, () => {
		if (workbook.doc.read_only) {
			workbook.autoSave = false
		}
	})
	return workbook
}

export function newWorkbookName() {
	const unique_id = getUniqueId()
	return `new-workbook-${unique_id}`
}

export function getLinkedQueries(query_name: string): string[] {
	const query = useQuery(query_name)
	const linkedQueries = new Set<string>()

	if (!query.isloaded) {
		console.log('Operations not loaded yet for query', query_name)
	}

	const operations = copy(query.currentOperations)
	if (query.activeEditIndex > -1) {
		operations.splice(query.activeEditIndex)
	}

	operations.forEach((op) => {
		if ('table' in op && 'type' in op.table && op.table.type === 'query') {
			linkedQueries.add(op.table.query_name)
		}
	})

	linkedQueries.forEach((q) => getLinkedQueries(q).forEach((q) => linkedQueries.add(q)))

	return Array.from(linkedQueries)
}
