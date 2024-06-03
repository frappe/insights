import { reactive } from 'vue'

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

		filters: [] as FilterArgs[],
		charts: [] as string[],

		addChart(chart: string) {
			dashboard.charts.push(chart)
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
