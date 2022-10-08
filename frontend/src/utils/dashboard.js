import { computed } from 'vue'
import { createDocumentResource, createResource } from 'frappe-ui'

export default function useDashboard(name) {
	const dashboard = makeDashboardResource(name)

	dashboard.updateNewChartOptions = () => {
		dashboard.getChartOptions.submit()
	}
	dashboard.newChartOptions = computed(() =>
		dashboard.getChartOptions.data?.message?.map((v) => {
			return {
				value: v.name,
				label: v.title,
				description: v.type,
			}
		})
	)
	dashboard.updateNewChartOptions()

	dashboard.editingLayout = false

	return dashboard
}

const getDashboardOptionsResource = createResource({
	method: 'insights.api.get_dashboard_options',
	initialData: [],
})
export function getDashboardOptions(query_chart) {
	return getDashboardOptionsResource.submit({ query_chart })
}
const createDashboardResource = createResource({
	method: 'insights.api.create_dashboard',
})
export function createDashboard(title) {
	return createDashboardResource.submit({ title })
}

function makeDashboardResource(name) {
	return createDocumentResource({
		doctype: 'Insights Dashboard',
		name: name,
		whitelistedMethods: {
			addChart: 'add_chart',
			getChartOptions: 'get_charts',
			refreshCharts: 'refresh_charts',
			removeChart: 'remove_chart',
			updateLayout: 'update_layout',
		},
	})
}
