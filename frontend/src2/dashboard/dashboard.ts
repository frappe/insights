import { reactive } from 'vue'
import { Chart, getCachedChart } from '../charts/chart'
import { getUniqueId } from '../helpers'
import { column } from '../query/helpers'
import {
	DashboardFilterColumn,
	WorkbookDashboard,
	WorkbookDashboardChart,
	WorkbookDashboardFilter,
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
		filters: [] as FilterArgs[],

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
					h: 2,
				},
			})
		},

		removeItem(index: number) {
			dashboard.doc.items.splice(index, 1)
		},

		applyFilter(filter: WorkbookDashboardFilter, operator: FilterOperator, value: FilterValue) {
			const charts = dashboard.doc.items.filter(
				(i) => i.type == 'chart'
			) as WorkbookDashboardChart[]
			charts.forEach((c) => {
				const chart = getCachedChart(c.chart) as Chart
				if (chart.doc.query == filter.column.query) {
					chart.applyFilter({
						column: column(filter.column.name),
						operator,
						value,
					})
				}
			})
		},

		refresh() {},
	})

	return dashboard
}

export type Dashboard = ReturnType<typeof makeDashboard>
