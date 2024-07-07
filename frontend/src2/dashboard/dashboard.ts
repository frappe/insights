import { reactive } from 'vue'
import { getCachedChart } from '../charts/chart'
import { getUniqueId, store } from '../helpers'
import { FilterArgs } from '../types/query.types'
import {
	DashboardFilterColumn,
	WorkbookChart,
	WorkbookDashboard,
	WorkbookDashboardChart,
} from '../types/workbook.types'

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
		filters: {} as Record<string, FilterArgs[]>,

		activeItemIdx: null as number | null,
		setActiveItem(index: number) {
			dashboard.activeItemIdx = index
		},
		isActiveItem(index: number) {
			return dashboard.activeItemIdx == index
		},

		addChart(charts: WorkbookChart[]) {
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
							y: 0,
							w: chart.chart_type === 'Number' ? 20 : 10,
							h: chart.chart_type === 'Number' ? 3 : 8,
						},
					})
				}
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

		applyFilter(query: string, args: FilterArgs) {
			if (!dashboard.filters[query]) dashboard.filters[query] = []
			dashboard.filters[query].push(args)
		},

		refresh() {
			dashboard.doc.items
				.filter((item): item is WorkbookDashboardChart => item.type === 'chart')
				.forEach((chartItem) => {
					const chart = getCachedChart(chartItem.chart)
					if (!chart || !chart.doc.query) return
					const filters = dashboard.filters[chart.doc.query]
					chart.refresh(filters, true)
				})
		},
	})

	const key = `insights:dashboard-filters-${workbookDashboard.name}`
	dashboard.filters = store(key, () => dashboard.filters)

	return dashboard
}

export type Dashboard = ReturnType<typeof makeDashboard>
