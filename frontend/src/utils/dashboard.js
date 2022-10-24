import { createResource } from 'frappe-ui'

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
