import { watchDebounced } from '@vueuse/core'
import { call } from 'frappe-ui'
import { computed, InjectionKey, reactive, toRefs } from 'vue'
import { useRouter } from 'vue-router'
import useChart from '../charts/chart'
import { handleOldYAxisConfig, setDimensionNames } from '../charts/helpers'
import useDashboard from '../dashboard/dashboard'
import { getUniqueId, safeJSONParse, showErrorToast, wheneverChanges } from '../helpers'
import { confirmDialog } from '../helpers/confirm_dialog'
import useDocumentResource from '../helpers/resource'
import { createToast } from '../helpers/toasts'
import useQuery, { getCachedQuery } from '../query/query'
import session from '../session'
import { Join, Source } from '../types/query.types'
import type {
	InsightsWorkbook,
	WorkbookChart,
	WorkbookSharePermission as WorkbookUserPermission,
} from '../types/workbook.types'

export default function useWorkbook(name: string) {
	const workbook = getWorkbookResource(name)

	workbook.onAfterInsert(() => {
		const href = window.location.href.replace(name, workbook.doc.name)
		window.location.replace(href)
	})

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

	const router = useRouter()
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
			chart_type: 'Bar',
			is_public: false,
			config: {} as WorkbookChart['config'],
			operations: [],
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

	let stopAutoSaveWatcher: any
	wheneverChanges(
		() => workbook.doc.enable_auto_save,
		() => {
			if (!workbook.doc.enable_auto_save && stopAutoSaveWatcher) {
				stopAutoSaveWatcher()
				stopAutoSaveWatcher = null
			}
			if (workbook.doc.enable_auto_save && !stopAutoSaveWatcher) {
				stopAutoSaveWatcher = watchDebounced(
					() => workbook.isdirty,
					() => workbook.isdirty && workbook.save(),
					{ immediate: true, debounce: 1000 }
				)
			}
		}
	)

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
		transform(doc: any) {
			doc.queries = safeJSONParse(doc.queries) || []
			doc.charts = safeJSONParse(doc.charts) || []
			doc.dashboards = safeJSONParse(doc.dashboards) || []

			doc.queries.forEach((query: any) => {
				if (!query.is_native_query && !query.is_script_query) {
					query.is_builder_query = true
				} else {
					query.is_builder_query = false
				}
			})

			doc.charts.forEach((chart: any) => {
				chart.config.filters = chart.config.filters?.filters?.length
					? chart.config.filters
					: {
							filters: [],
							logical_operator: 'And',
					  }
				chart.config.order_by = chart.config.order_by || []
				chart.config.limit = chart.config.limit || 100

				if ('y_axis' in chart.config && Array.isArray(chart.config.y_axis)) {
					// @ts-ignore
					chart.config.y_axis = handleOldYAxisConfig(chart.config.y_axis)
				}
				chart.config = setDimensionNames(chart.config)
			})
			return doc
		},
	})

	workbook.onAfterLoad(() => workbook.call('track_view').catch(() => {}))
	return workbook
}

export function newWorkbookName() {
	const unique_id = getUniqueId()
	return `new-workbook-${unique_id}`
}
