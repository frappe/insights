import { reactive } from 'vue'

export default function useDashboard(name: string) {
	const dashboard = reactive({
		name,
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

export type Dashboard = ReturnType<typeof useDashboard>
