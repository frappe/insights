import { reactive, computed } from 'vue'
import { createDocumentResource } from 'frappe-ui'

export default function useDashboard(name) {
	const dashboard = makeDashboardResource(name)

	dashboard.getVisualizations.submit()
	dashboard.newVisualizationOptions = computed(() =>
		dashboard.getVisualizations.data?.message?.map((v) => {
			return {
				value: v.name,
				label: v.title,
				description: v.type,
			}
		})
	)

	dashboard.editingLayout = false

	return dashboard
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
