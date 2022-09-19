import { computed } from 'vue'
import { createDocumentResource, createResource } from 'frappe-ui'

export default function useDashboard(name) {
	const dashboard = makeDashboardResource(name)

	dashboard.updateNewVisualizationOptions = () => {
		dashboard.getVisualizations.submit()
	}
	dashboard.newVisualizationOptions = computed(() =>
		dashboard.getVisualizations.data?.message?.map((v) => {
			return {
				value: v.name,
				label: v.title,
				description: v.type,
			}
		})
	)
	dashboard.updateNewVisualizationOptions()

	dashboard.editingLayout = false

	return dashboard
}

const getDashboardOptionsResource = createResource({
	method: 'insights.api.get_dashboard_options',
	initialData: [],
})
export function getDashboardOptions(visualization) {
	return getDashboardOptionsResource.submit({ visualization })
}

function makeDashboardResource(name) {
	return createDocumentResource({
		doctype: 'Insights Dashboard',
		name: name,
		whitelistedMethods: {
			addVisualization: 'add_visualization',
			getVisualizations: 'get_visualizations',
			refreshVisualizations: 'refresh_visualizations',
			removeVisualization: 'remove_visualization',
			updateLayout: 'update_layout',
		},
	})
}
