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

type FilterState = {
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

		activeItemIdx: null as number | null,
		setActiveItem(index: number) {
			dashboard.activeItemIdx = index
		},
		isActiveItem(index: number) {
			return dashboard.activeItemIdx == index
		},
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
				text: '',
				layout: {
					i: getUniqueId(),
					x: 0,
					y: maxY,
					w: 10,
					h: 2,
				},
			})
			dashboard.editingItemIndex = dashboard.doc.items.length - 1
			dashboard.setActiveItem(dashboard.doc.items.length - 1)
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
			dashboard.setActiveItem(dashboard.doc.items.length - 1)
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

			const dependentQueries = chart.getDependentQueries()
			dependentQueries.forEach((query) => {
				const _query = getCachedQuery(query)
				if (!_query) return
				_query.dashboardFilters = {
					logical_operator: 'And',
					filters: dashboard.getQueryFilters(query),
				}
			})

			chart.refresh(undefined, true)
		},

		getQueryFilters(query: string) {
			const filterItems = dashboard.doc.items.filter(
				(item) => item.type === 'filter' && item.links[query]
			)
			return filterItems
				.map((item) => {
					const filterItem = item as WorkbookDashboardFilter
					const linkedColumn = filterItem.links[query]
					if (!linkedColumn) return

					const state = dashboard.filterStates[filterItem.filter_name] || {}
					const filter = {
						column: column(linkedColumn),
						operator: state.operator,
						value: state.value,
					}

					if (isFilterValid(filter, filterItem.filter_type)) {
						return filter
					}
				})
				.filter(Boolean) as FilterRule[]
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
			const filterQueries = Object.keys(filterItem.links)

			const charts = dashboard.doc.items.filter((i) => i.type === 'chart')
			charts.forEach((chartItem) => {
				const chart = getCachedChart(chartItem.chart)
				if (!chart) return

				const chartQueries = chart.getDependentQueries()
				if (chartQueries.some((query) => filterQueries.includes(query))) {
					dashboard.refreshChart(chartItem.chart)
				}
			})
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

	const key = `insights:dashboard-filters-${workbookDashboard.name}`
	dashboard.filters = store(key, () => dashboard.filters)

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

	return dashboard
}

export type Dashboard = ReturnType<typeof makeDashboard>
