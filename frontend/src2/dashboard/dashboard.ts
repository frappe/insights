import { reactive } from 'vue'
import { getCachedChart } from '../charts/chart'
import { getUniqueId, store } from '../helpers'
import { isFilterValid } from '../query/components/filter_utils'
import { column } from '../query/helpers'
import { getCachedQuery } from '../query/query'
import { FilterArgs, FilterOperator, FilterRule, FilterValue } from '../types/query.types'
import {
	WorkbookChart,
	WorkbookDashboard,
	WorkbookDashboardFilter,
	WorkbookDashboardItem,
} from '../types/workbook.types'

const dashboards = new Map<string, Dashboard>()

export default function useDashboard(workbookDashboard: WorkbookDashboard) {
	const existingDashboard = dashboards.get(workbookDashboard.name)
	if (existingDashboard) return existingDashboard

	const dashboard = makeDashboard(workbookDashboard)
	dashboards.set(workbookDashboard.name, dashboard)
	return dashboard
}

export type FilterState = {
	operator: FilterOperator
	value: FilterValue
}

function makeDashboard(workbookDashboard: WorkbookDashboard) {
	const dashboard = reactive({
		doc: workbookDashboard,

		editing: false,
		editingItemIndex: null as number | null,
		filters: {} as Record<string, FilterArgs[]>,
		filterStates: {} as Record<string, FilterState>,

		isEditingItem(item: WorkbookDashboardItem) {
			return dashboard.editing && dashboard.editingItemIndex === dashboard.doc.items.indexOf(item)
		},

		addChart(charts: WorkbookChart[]) {
			const maxY = dashboard.getMaxY()
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
		},

		addText() {
			const maxY = dashboard.getMaxY()
			dashboard.doc.items.push({
				type: 'text',
				text: 'Enter text here',
				layout: {
					i: getUniqueId(),
					x: 0,
					y: maxY,
					w: 10,
					h: 1,
				},
			})
			dashboard.editingItemIndex = dashboard.doc.items.length - 1
		},

		addFilter() {
			const maxY = dashboard.getMaxY()
			dashboard.doc.items.push({
				type: 'filter',
				filter_name: 'Filter',
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
			dashboard.editingItemIndex = dashboard.doc.items.length - 1
		},

		removeItem(index: number) {
			dashboard.doc.items.splice(index, 1)
		},

		refresh() {
			dashboard.doc.items
				.filter((item) => item.type === 'chart')
				.forEach((item) => dashboard.refreshChart(item.chart))
		},

		refreshChart(chart_name: string) {
			const chart = getCachedChart(chart_name)
			if (!chart || !chart.doc.query) return

			const filtersApplied = dashboard.doc.items.filter(
				(item) => item.type === 'filter' && 'links' in item && item.links[chart_name]
			)

			if (!filtersApplied.length) {
				chart.refresh(undefined, true)
				return
			}

			const filtersByQuery = new Map<string, FilterRule[]>()

			filtersApplied.forEach((item) => {
				const filterItem = item as WorkbookDashboardFilter
				const linkedColumn = dashboard.getColumnFromFilterLink(filterItem.links[chart_name])
				if (!linkedColumn) return

				const query = getCachedQuery(linkedColumn.query)
				if (!query) return

				const filterState = dashboard.filterStates[filterItem.filter_name] || {}

				const filter = {
					column: column(linkedColumn.column),
					operator: filterState.operator,
					value: filterState.value,
				}

				if (isFilterValid(filter, filterItem.filter_type)) {
					const filters = filtersByQuery.get(linkedColumn.query) || []
					filters.push(filter)
					filtersByQuery.set(linkedColumn.query, filters)
				}
			})

			filtersByQuery.forEach((filters, query_name) => {
				const query = getCachedQuery(query_name)!
				query.dashboardFilters = {
					logical_operator: 'And',
					filters,
				}
			})

			chart.refresh(undefined, true)
		},

		updateFilterState(filter_name: string, operator?: FilterOperator, value?: FilterValue) {
			const filter = dashboard.doc.items.find(
				(item) => item.type === 'filter' && item.filter_name === filter_name
			)
			if (!filter) return

			if (!operator) {
				delete dashboard.filterStates[filter_name]
			} else {
				dashboard.filterStates[filter_name] = {
					operator,
					value,
				}
			}

			dashboard.applyFilter(filter_name)
		},

		applyFilter(filter_name: string) {
			const item = dashboard.doc.items.find(
				(item) => item.type === 'filter' && item.filter_name === filter_name
			)
			if (!item) return

			const filterItem = item as WorkbookDashboardFilter
			const filteredCharts = Object.keys(filterItem.links)
			filteredCharts.forEach((chart_name) => dashboard.refreshChart(chart_name))
		},

		getColumnFromFilterLink(linkedColumn: string) {
			const sep = '`'
			// `query`.`column`
			const pattern = new RegExp(`^${sep}([^${sep}]+)${sep}\\.${sep}([^${sep}]+)${sep}$`)
			const match = linkedColumn.match(pattern)
			if (!match) return

			return {
				query: match[1],
				column: match[2],
			}
		},

		getShareLink() {
			return (
				dashboard.doc.share_link ||
				`${window.location.origin}/insights/shared/dashboard/${dashboard.doc.name}`
			)
		},

		getMaxY() {
			return Math.max(...dashboard.doc.items.map((item) => item.layout.y + item.layout.h), 0)
		},
	})

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
	}, {} as typeof dashboard.filterStates)

	Object.assign(dashboard.filterStates, defaultFilters)

	const key2 = `insights:dashboard-filter-states-${workbookDashboard.name}`
	dashboard.filterStates = store(key2, () => dashboard.filterStates)

	return dashboard
}

export type Dashboard = ReturnType<typeof makeDashboard>
