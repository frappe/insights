import { reactive } from 'vue'
import { Analysis } from './useAnalysis'
import { AnalysisChart } from './useAnalysisChart'
import storeLocally from './storeLocally'

export function useAnalysisDashboard(name: string, analysis: Analysis) {
	const dashboard = reactive({
		name,
		filters: [] as FilterArgs[],
		charts: [] as AnalysisChart[],

		addChart(chart: AnalysisChart) {
			dashboard.charts.push(chart)
		},

		setFilters(filters: FilterArgs[]) {
			dashboard.filters = filters
			dashboard.refresh()
		},

		refresh() {
			dashboard.charts.forEach(chart => chart.setFilters(dashboard.filters))
			dashboard.charts.forEach(chart => chart.refresh())
		},

		serialize() {
			return {
				name: dashboard.name,
				filters: dashboard.filters,
			}
		},
	})

	const storedDashboard = storeLocally<AnalysisDashboardSerialized>({
		key: 'name',
		namespace: 'insights:analysis-dashboard:',
		serializeFn: dashboard.serialize,
		defaultValue: {} as AnalysisDashboardSerialized,
	})
	if (storedDashboard.value.name === dashboard.name) {
		Object.assign(dashboard, storedDashboard.value)
	}

	return dashboard
}

export type AnalysisDashboard = ReturnType<typeof useAnalysisDashboard>
export type AnalysisDashboardSerialized = ReturnType<AnalysisDashboard['serialize']>
