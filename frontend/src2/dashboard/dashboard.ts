import { reactive } from 'vue'
import { WorkbookDashboard } from '../workbook/workbook'
import { getUniqueId } from '../helpers'

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

		editing: true,
		filters: [] as FilterArgs[],

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
						w: 6,
						h: 12,
					},
				})
			})
		},

		setFilters(filters: FilterArgs[]) {
			dashboard.filters = filters
			dashboard.refresh()
		},

		refresh() {
			// dashboard.charts.forEach(chart => chart.setFilters(dashboard.filters))
			// dashboard.charts.forEach(chart => chart.refresh())
		},
	})

	return dashboard
}

export type Dashboard = ReturnType<typeof makeDashboard>
