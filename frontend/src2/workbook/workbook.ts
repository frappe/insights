import { call, toast } from 'frappe-ui'
import { __ } from '../translation'
import { useTelemetry } from '../telemetry'
import { computed, reactive, toRefs } from 'vue'
import useChart, { newChart } from '../charts/chart'
import useDashboard, { newDashboard } from '../dashboard/dashboard'
import {
	copyToClipboard,
	getUniqueId,
	safeJSONParse,
	showErrorToast,
	waitUntil,
	wheneverChanges,
} from '../helpers'
import { confirmDialog } from '../helpers/confirm_dialog'
import useDocumentResource from '../helpers/resource'
import { getLinkedQueries } from '../query/linked_queries'
import useQuery, { newQuery } from '../query/query'
import router from '../router'
import session from '../session'
import type { Operation } from '../types/query.types'
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
	const { capture } = useTelemetry()
	const workbook = getWorkbookResource(name)

	// getLinkedQueries expects the query to be loaded
	wheneverChanges(
		() => workbook.doc.queries.map((q) => q.name),
		() => workbook.doc.queries.forEach((q) => useQuery(q.name)),
		{ deep: true },
	)

	function setActiveTab(type: 'query' | 'chart' | 'dashboard', name: string) {
		router.replace(`/workbook/${workbook.name}/${type}/${name}`)
	}
	function isActiveTab(type: 'query' | 'chart' | 'dashboard', name: string) {
		const url = router.currentRoute.value.path
		const regex = new RegExp(`/workbook/${workbook.name}/${type}/${name}`)
		return regex.test(url)
	}

	type QuerySeed = {
		title?: string
		operations?: Operation[]
		use_live_connection?: boolean
	}
	async function addQuery(seed: QuerySeed = {}) {
		const query = newQuery()
		query.doc.title = seed.title || 'Query ' + (workbook.doc.queries.length + 1)
		query.doc.workbook = workbook.doc.name
		query.doc.use_live_connection = seed.use_live_connection ?? true
		query.doc.sort_order = workbook.doc.queries.length
		query.doc.folder = null
		if (seed.operations) {
			query.doc.operations = seed.operations
		}
		return query.insert().then(() => {
			workbook.doc.queries.push({
				name: query.doc.name,
				title: query.doc.title,
				sort_order: query.doc.sort_order,
				folder: null,
			})
			setActiveTab('query', query.doc.name)
			return query
		})
	}

	function removeQuery(name: string) {
		confirmDialog({
			title: __('Delete Query'),
			message: __('Are you sure you want to delete this query?'),
			onSuccess: () => removeItem('query', useQuery(name)),
		})
	}

	function addChart(query_name?: string) {
		const chart = newChart()
		chart.doc.title = 'Chart ' + (workbook.doc.charts.length + 1)
		chart.doc.workbook = workbook.doc.name
		chart.doc.query = query_name || ''
		chart.doc.chart_type = 'Bar'
		chart.doc.sort_order = workbook.doc.charts.length
		chart.doc.folder = null
		chart.insert().then(() => {
			workbook.doc.charts.push({
				name: chart.doc.name,
				title: chart.doc.title,
				query: chart.doc.query,
				chart_type: 'Bar',
				sort_order: chart.doc.sort_order,
				folder: null,
			})
			capture('chart_created')
			setActiveTab('chart', chart.doc.name)
		})
	}

	function removeChart(chartName: string) {
		confirmDialog({
			title: __('Delete Chart'),
			message: __('Are you sure you want to delete this chart?'),
			onSuccess: () => removeItem('chart', useChart(chartName)),
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
			capture('dashboard_created')
			setActiveTab('dashboard', dashboard.doc.name)
		})
	}

	function removeDashboard(dashboardName: string) {
		confirmDialog({
			title: __('Delete Dashboard'),
			message: __('Are you sure you want to delete this dashboard?'),
			onSuccess: () => removeItem('dashboard', useDashboard(dashboardName)),
		})
	}

	// The row stays until the server deletes the document: a refused delete
	// (a desk document draws it) leaves the author where they were.
	async function removeItem(
		type: 'query' | 'chart' | 'dashboard',
		item: { name: string; isloaded: boolean; delete: () => Promise<void> },
	) {
		await waitUntil(() => item.isloaded)
		await item.delete()

		const rows = {
			query: workbook.doc.queries,
			chart: workbook.doc.charts,
			dashboard: workbook.doc.dashboards,
		}[type]
		const idx = rows.findIndex((row) => row.name === item.name)
		if (idx === -1) return
		rows.splice(idx, 1)
		openNext(type, idx)
	}

	// Called after the row at `idx` is spliced out, so `idx` now holds the row
	// that took its place — the next tab of the same type, or the last one.
	function openNext(type: 'query' | 'chart' | 'dashboard', idx: number) {
		const items = {
			query: workbook.doc.queries,
			chart: workbook.doc.charts,
			dashboard: workbook.doc.dashboards,
		}[type]

		const next = items[Math.min(idx, items.length - 1)]
		if (next) {
			setActiveTab(type, next.name)
			return
		}

		// The last chart or dashboard is gone. A workbook always holds a query,
		// so that is the tab to land on rather than a route with no document.
		const query = workbook.doc.queries[0]
		if (query) {
			setActiveTab('query', query.name)
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
						full_name: p.full_name || p.user,
						user_image: p.user_image,
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
		})
	}

	function duplicate() {
		confirmDialog({
			title: __('Duplicate Workbook'),
			message: __(
				'Duplicating this workbook will create a new workbook and copy all queries, charts and dashboards to it. Do you want to continue?',
			),
			onSuccess: () => {
				workbook
					.call('duplicate')
					.then((name: any) => {
						toast.success(__('Workbook duplicated successfully'))
						window.location.href = router.resolve({
							name: 'Workbook',
							params: { workbook_name: name },
						}).href
					})
					.catch(showErrorToast)
			},
		})
	}

	function importQuery(query: any) {
		confirmDialog({
			title: __('Import Query'),
			message: __('Are you sure you want to import this query?'),
			onSuccess: () => {
				workbook.call('import_query', { query }).then((name) => {
					workbook.load().then(() => {
						toast.success(__('Query imported successfully'))
						setActiveTab('query', name)
					})
				})
			},
		})
	}

	function importChart(chart: any) {
		confirmDialog({
			title: __('Import Chart'),
			message: __('Are you sure you want to import this chart?'),
			onSuccess: () => {
				workbook.call('import_chart', { chart }).then((name) => {
					workbook.load().then(() => {
						toast.success(__('Chart imported successfully'))
						setActiveTab('chart', name)
					})
				})
			},
		})
	}

	function copyJSON() {
		copyToClipboard(workbook.call('export').then((data) => JSON.stringify(data, null, 2)))
	}

	function deleteWorkbook() {
		confirmDialog({
			title: __('Delete Workbook'),
			message: __('Are you sure you want to delete this workbook?'),
			theme: 'red',
			onSuccess: () => workbook.delete().then(() => router.replace('/workbook')),
		})
	}

	async function addFolder(title: string = 'New Folder', folderType: 'query' | 'chart') {
		const method = 'insights.api.workbooks.create_folder'
		return call(method, { workbook: workbook.name, title, folder_type: folderType })
			.then(() => {
				workbook.load()
			})
			.catch(showErrorToast)
	}

	function removeFolder(folderName: string) {
		function _remove() {
			const method = 'insights.api.workbooks.delete_folder'
			call(method, { folder_name: folderName, move_items_to_root: true })
				.then(() => {
					workbook.load()
				})
				.catch(showErrorToast)
		}

		confirmDialog({
			title: __('Delete Folder'),
			message: __('This will move all items in the folder to the root. Continue?'),
			onSuccess: _remove,
		})
	}

	async function renameFolder(folderName: string, newTitle: string) {
		const method = 'insights.api.workbooks.rename_folder'
		return call(method, { folder_name: folderName, new_title: newTitle })
			.then(() => {
				workbook.load()
			})
			.catch(showErrorToast)
	}

	async function moveItemToFolder(
		itemType: 'query' | 'chart',
		itemName: string,
		folderName?: string,
	) {
		const method = 'insights.api.workbooks.move_item_to_folder'
		return call(method, {
			item_type: itemType,
			item_name: itemName,
			folder_name: folderName || null,
		})
			.then(() => workbook.load())
			.catch(showErrorToast)
	}

	async function updateSortOrder(
		items: Array<{ type: string; name: string; sort_order: number; folder?: string | null }>,
	) {
		const method = 'insights.api.workbooks.update_sort_orders'
		return call(method, { workbook: workbook.name, items }).catch(showErrorToast)
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

		addFolder,
		removeFolder,
		renameFolder,
		moveItemToFolder,
		updateSortOrder,

		getSharePermissions,
		updateSharePermissions,

		getLinkedQueries,

		copy: copyJSON,

		openInDesk() {
			window.open(`/app/insights-workbook/${workbook.name}`, '_blank')
		},

		delete: deleteWorkbook,
	})
}

export type Workbook = ReturnType<typeof makeWorkbook>

// Where this open came from. The page has two signals: the history entry it was
// pushed from, and the referrer when there is none. Every other arrival is a
// link.
function openedVia() {
	const back = router.options.history.state.back
	if (back === '/workbook') return 'list'
	if (back === '/') return 'recent'
	if (!back && document.referrer.startsWith(`${location.origin}/app`)) return 'desk'
	return 'link'
}

export function getWorkbookResource(name: string) {
	const doctype = 'Insights Workbook'
	const workbook = useDocumentResource<InsightsWorkbook>(doctype, name, {
		initialDoc: {
			doctype,
			name,
			owner: '',
			title: '',
			folders: [],
			queries: [],
			charts: [],
			dashboards: [],
			read_only: false,
		},
		enableAutoSave: true,
		disableLocalStorage: true,
		transform(doc: any) {
			doc.folders = safeJSONParse(doc.folders) || []
			doc.queries = safeJSONParse(doc.queries) || []
			doc.charts = safeJSONParse(doc.charts) || []
			doc.dashboards = safeJSONParse(doc.dashboards) || []
			return doc
		},
	})

	workbook.onAfterLoad(() => workbook.call('track_view', { via: openedVia() }).catch(() => {}))
	wheneverChanges(
		() => workbook.doc.read_only,
		() => {
			if (workbook.doc.read_only) {
				workbook.autoSave = false
			}
		},
	)
	return workbook
}

export function newWorkbookName() {
	const unique_id = getUniqueId()
	return `new-workbook-${unique_id}`
}
