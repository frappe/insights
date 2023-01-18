import { createResource } from 'frappe-ui'

const getDashboardOptionsResource = createResource({
	url: 'insights.api.get_dashboard_options',
	initialData: [],
})
export function getDashboardOptions(chart) {
	return getDashboardOptionsResource.submit({ chart })
}
const createDashboardResource = createResource({
	url: 'insights.api.create_dashboard',
})
export function createDashboard(title) {
	return createDashboardResource.submit({ title })
}
