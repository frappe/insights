import { reactive } from 'vue'
import { Chart, getCachedChart } from '../charts/chart'
import { getUniqueId } from '../helpers'
import { column as make_column } from '../query/helpers'
import {
	DashboardFilterColumn,
	WorkbookDashboard,
	WorkbookDashboardChart,
} from '../workbook/workbook'

const dashboards = new Map<string, Dashboard>()

export default function useDashboard(workbookDashboard: WorkbookDashboard) {
	const existingDashboard = dashboards.get(workbookDashboard.name)
	if (existingDashboard) return existingDashboard

	const dashboard = makeDashboard(workbookDashboard)
	dashboards.set(workbookDashboard.name, dashboard)
	return dashboard
}

function makeDashboard(workbookDashboard: WorkbookDashboard) {
	const dashboard = reactive({
		doc: workbookDashboard,

		editing: false,
		filters: new Map<string, FilterArgs[]>(),

		activeItemIdx: null as number | null,
		setActiveItem(index: number) {
			dashboard.activeItemIdx = index
		},
		isActiveItem(index: number) {
			return dashboard.activeItemIdx == index
		},

		addChart(chart: string[] | string) {
			const _chart = Array.isArray(chart) ? chart : [chart]
			_chart.forEach((chart) => {
				dashboard.doc.items.push({
					type: 'chart',
					chart,
					layout: {
						i: getUniqueId(),
						x: 0,
						y: 0,
						w: 10,
						h: 12,
					},
				})
			})
		},

		addFilter(column: DashboardFilterColumn) {
			dashboard.doc.items.push({
				type: 'filter',
				column: column,
				layout: {
					i: getUniqueId(),
					x: 0,
					y: 0,
					w: 4,
					h: 1,
				},
			})
		},

		removeItem(index: number) {
			dashboard.doc.items.splice(index, 1)
		},

		applyFilter(column: DashboardFilterColumn, operator: FilterOperator, value: FilterValue) {
			const queryFilters = dashboard.filters.get(column.query) || []
			queryFilters.push({
				column: make_column(column.name),
				operator,
				value,
			})
			dashboard.filters.set(column.query, queryFilters)
			dashboard.refresh()
		},

		refresh() {
			dashboard.doc.items
				.filter((item): item is WorkbookDashboardChart => item.type === 'chart')
				.forEach((chartItem) => {
					const chart = getCachedChart(chartItem.chart) as Chart
					const filters = dashboard.filters.get(chart.doc.query)
					if (chart && filters?.length) chart.refresh(filters)
				})
		},
	})

	return dashboard
}

export type Dashboard = ReturnType<typeof makeDashboard>
