import { reactive, ref, toRefs } from 'vue'
import useChart from '../charts/chart'
import {
	getUniqueId,
	safeJSONParse,
	showErrorToast,
	store,
	waitUntil,
	wheneverChanges,
} from '../helpers'
import useDocumentResource from '../helpers/resource'
import { isFilterValid } from '../query/components/filter_utils'
import { column, filter_group } from '../query/helpers'
import session from '../session'
import { FilterArgs, FilterGroup, FilterOperator, FilterValue } from '../types/query.types'
import {
	InsightsDashboardv3,
	WorkbookChart,
	WorkbookDashboardFilter,
	WorkbookDashboardItem,
} from '../types/workbook.types'
import useWorkbook from '../workbook/workbook'

const dashboards = new Map<string, Dashboard>()

export default function useDashboard(name: string) {
	const key = String(name)
	const existingDashboard = dashboards.get(key)
	if (existingDashboard) return existingDashboard

	const dashboard = makeDashboard(name)
	dashboards.set(key, dashboard)
	return dashboard
}

export type FilterState = {
	operator: FilterOperator
	value: FilterValue
}

function makeDashboard(name: string) {
	const dashboard = getDashboardResource(name)

	const editing = ref(false)
	const editingItemIndex = ref<number>()

	function isEditingItem(item: WorkbookDashboardItem) {
		return editing.value && editingItemIndex.value === dashboard.doc.items.indexOf(item)
	}


	const filters = ref<Record<string, FilterArgs[]>>({})
	const filterStates = ref<Record<string, FilterState>>({})


	function addChart(charts: WorkbookChart[]) {
		const maxY = getMaxY()
		charts.forEach((chart) => {
			if (
				!dashboard.doc.items.some((item) => item.type === 'chart' && item.chart === chart.name)
			) {
				dashboard.doc.items.push({
					type: 'chart',
					chart: chart.name,
					layout: {
						i: getUniqueId(),
						x: 0,
						y: maxY,
						w: chart.chart_type === 'Number' ? 20 : 10,
						h: chart.chart_type === 'Number' ? 3 : 8,
					},
				})
			}
		})
	}

	function getMaxY() {
		return Math.max(...dashboard.doc.items.map((item) => item.layout.y + item.layout.h), 0)
	}

	function addText() {
		const maxY = getMaxY()
		dashboard.doc.items.push({
			type: 'text',
			text: '',
			layout: {
				i: getUniqueId(),
				x: 0,
				y: maxY,
				w: 10,
				h: 1,
			},
		})
		editingItemIndex.value = dashboard.doc.items.length - 1
	}

	function addFilter() {
		const maxY = getMaxY()
		dashboard.doc.items.push({
			type: 'filter',
			filter_name: '',
			filter_type: 'String',
			links: {},
			layout: {
				i: getUniqueId(),
				x: 0,
				y: maxY,
				w: 4,
				h: 1,
			},
		})
		editingItemIndex.value = dashboard.doc.items.length - 1
	}

	function removeItem(index: number) {
		dashboard.doc.items.splice(index, 1)
	}

	function refresh() {
		dashboard.doc.items
			.filter((item) => item.type === 'chart')
			.forEach((item) => refreshChart(item.chart))
	}

	function refreshChart(chart_name: string) {
		const chart = useChart(chart_name)
		chart.refresh({
			adhocFilters: getAdhocFilters(chart_name),
		})
	}

	function getAdhocFilters(chart_name: string) {
		const filtersApplied = dashboard.doc.items.filter(
			(item) => item.type === 'filter' && 'links' in item && item.links[chart_name]
		)

		if (filtersApplied.length === 0) return

		const filtersByQuery = {} as Record<string, FilterGroup>

		function addFilterToQuery(query_name: string, filter: FilterArgs) {
			if (!filtersByQuery[query_name]) {
				filtersByQuery[query_name] = filter_group({
					logical_operator: 'And',
					filters: [],
				})
			}
			filtersByQuery[query_name].filters.push(filter)
		}

		filtersApplied.forEach((item) => {
			const filterItem = item as WorkbookDashboardFilter
			const linkedColumn = getColumnFromFilterLink(filterItem.links[chart_name])
			if (!linkedColumn) return

			const filterState = filterStates.value[filterItem.filter_name] || {}

			const filter = {
				column: column(linkedColumn.column),
				operator: filterState.operator,
				value: filterState.value,
			}

			if (isFilterValid(filter, filterItem.filter_type)) {
				addFilterToQuery(linkedColumn.query, filter)
			}
		})

		return filtersByQuery
	}

	function updateFilterState(filter_name: string, operator?: FilterOperator, value?: FilterValue) {
		const filter = dashboard.doc.items.find(
			(item) => item.type === 'filter' && item.filter_name === filter_name
		)
		if (!filter) return

		if (!operator) {
			delete filterStates.value[filter_name]
		} else {
			filterStates.value[filter_name] = {
				operator,
				value,
			}
		}

		applyFilter(filter_name)
	}

	function applyFilter(filter_name: string) {
		const item = dashboard.doc.items.find(
			(item) => item.type === 'filter' && item.filter_name === filter_name
		)
		if (!item) return

		const filterItem = item as WorkbookDashboardFilter
		const filteredCharts = Object.keys(filterItem.links).filter(
			(chart_name) => filterItem.links[chart_name]
		)
		filteredCharts.forEach((chart_name) => refreshChart(chart_name))
	}

	function getColumnFromFilterLink(linkedColumn: string) {
		const sep = '`'
		// `query`.`column`
		const pattern = new RegExp(`^${sep}([^${sep}]+)${sep}\\.${sep}([^${sep}]+)${sep}$`)
		const match = linkedColumn.match(pattern)
		if (!match || match.length < 3) return null

		return {
			query: match[1],
			column: match[2],
		}
	}

	function getDistinctColumnValues(query: string, column: string, search_term?: string) {
		return dashboard.call('get_distinct_column_values', {
			query: query,
			column_name: column,
			search_term,
		})
	}

	function getShareLink() {
		return (
			dashboard.doc.share_link ||
			`${window.location.origin}/insights/shared/dashboard/${dashboard.doc.name}`
		)
	}

	function updateAccess(data: {
		is_public: boolean
		is_shared_with_organization: boolean
		people_with_access: string[]
	}) {
		return dashboard
			.call('update_access', { data })
			.catch(showErrorToast)
			.then(() => dashboard.load())
	}


	const defaultFilters = dashboard.doc.items.reduce((acc, item) => {
		if (item.type != 'filter') return acc

		const filterItem = item as WorkbookDashboardFilter
		if (filterItem.default_operator && filterItem.default_value) {
			acc[filterItem.filter_name] = {
				operator: filterItem.default_operator,
				value: filterItem.default_value,
			}
		}
		return acc
	}, {} as typeof filterStates.value)

	Object.assign(filterStates.value, defaultFilters)

	const key = `insights:dashboard-filter-states-${name}`
	filterStates.value = store(key, () => filterStates.value)

	waitUntil(() => dashboard.isloaded).then(() => {
		wheneverChanges(
			() => dashboard.doc.title,
			() => {
				if (!dashboard.doc.workbook) return
				const workbook = useWorkbook(dashboard.doc.workbook)
				for (const d of workbook.doc.dashboards) {
					if (d.name === dashboard.doc.name) {
						d.title = dashboard.doc.title
						break
					}
				}
			},
			{ debounce: 500 }
		)
	})

	return reactive({
		...toRefs(dashboard),

		editing,
		editingItemIndex,
		isEditingItem,

		filters,
		filterStates,

		addChart,
		addText,
		addFilter,
		removeItem,

		refresh,
		refreshChart,

		updateFilterState,
		applyFilter,
		getColumnFromFilterLink,

		getDistinctColumnValues,
		updateAccess,

		getShareLink,
	})
}

export type Dashboard = ReturnType<typeof makeDashboard>

const INITIAL_DOC: InsightsDashboardv3 = {
	doctype: 'Insights Dashboard v3',
	name: '',
	owner: '',
	title: '',
	workbook: '',
	items: [],
	is_public: false,
	is_shared_with_organization: false,
	people_with_access: [],
	read_only: false,
}

function getDashboardResource(name: string) {
	const doctype = 'Insights Dashboard v3'
	const dashboard = useDocumentResource<InsightsDashboardv3>(doctype, name, {
		initialDoc: { ...INITIAL_DOC, name },
		enableAutoSave: true,
		disableLocalStorage: true,
		transform(doc: any) {
			doc.items = safeJSONParse(doc.items) || []
			return doc
		},
	})
	if (session.isLoggedIn) {
		dashboard.onAfterLoad(() => dashboard.call('track_view').catch(() => { }))
	}
	wheneverChanges(() => dashboard.doc.read_only, () => {
		if (dashboard.doc.read_only) {
			dashboard.autoSave = false
		}
	})
	return dashboard
}

export function newDashboard() {
	return getDashboardResource('new-dashboard-' + getUniqueId())
}
