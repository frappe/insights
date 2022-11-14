import { computed, ref } from 'vue'
import { safeJSONParse } from '@/utils'
import { createDocumentResource, call } from 'frappe-ui'

export default function useDashboard(dashboardName) {
	const dashboard = makeDashboardResource(dashboardName)

	// reactive properties
	dashboard.editing = false
	dashboard.updatedLayout = {}
	dashboard.items = computed(() =>
		dashboard.doc?.items.map((v) => {
			const layout = safeJSONParse(v.layout, {})
			return {
				...v,
				...layout,
			}
		})
	)

	// methods
	dashboard.updateNewChartOptions = () => {
		dashboard.get_chart_options.submit()
	}
	dashboard.newChartOptions = computed(() =>
		dashboard.get_chart_options.data?.message?.map((v) => {
			return {
				value: v.name,
				label: v.title,
				description: v.type,
			}
		})
	)
	dashboard.updateLayout = (changedItems) => {
		changedItems.forEach((item) => {
			const name = item.id
			delete item.id
			dashboard.updatedLayout[name] = item
		})
	}
	dashboard.commitLayout = () => {
		dashboard.update_layout
			.submit({
				updated_layout: dashboard.updatedLayout,
			})
			.then(() => {
				dashboard.editingLayout = false
			})
	}
	dashboard.addItem = (item) => {
		let layout = { w: 8, h: 8, x: 0, y: 0 }
		if (item.item_type === 'Filter') {
			layout = { w: 4, h: 3, x: 0, y: 0 }
		}
		return dashboard.add_item.submit({ item, layout }).then(() => {
			dashboard.updateNewChartOptions()
		})
	}

	dashboard.removeItem = (name) => {
		dashboard.remove_item
			.submit({
				item: name,
			})
			.then(() => {
				dashboard.updateNewChartOptions()
			})
	}

	dashboard.editChart = (chartID) => {
		call('frappe.client.get_value', {
			doctype: 'Insights Query Chart',
			filters: { name: chartID },
			fieldname: 'query',
		}).then((r) => {
			window.open(`/insights/query/${r.query}`, '_blank')
		})
	}

	dashboard.deletingDashboard = computed(() => dashboard.delete.loading)
	dashboard.deleteDashboard = () => {
		return dashboard.delete.submit()
	}

	dashboard.refreshItems = async () => {
		dashboard.refreshing = true
		// hack: update the charts
		await dashboard.refresh_items.submit()
		// then reload the dashboard doc
		// to re-render the charts with new data
		dashboard.doc.items = []
		await dashboard.reload()
		dashboard.refreshing = false
	}

	dashboard.getChartData = (chartID) => {
		const data = ref([])
		dashboard.get_chart_data.submit({ chart: chartID }).then((r) => {
			data.value = r.message
		})
		return computed(() => safeJSONParse(data.value, []))
	}

	dashboard.filters = computed(() => dashboard.doc?.items.filter((v) => v.item_type == 'Filter'))

	dashboard.getAllColumns = (query) => {
		dashboard.get_all_columns.submit({ query })
		return computed(() => dashboard.get_all_columns.data?.message || [])
	}

	dashboard.getColumns = (query) => {
		dashboard.get_columns.submit({ query })
		return computed(() => dashboard.get_columns.data?.message || [])
	}

	dashboard.updateNewChartOptions()
	return dashboard
}

function makeDashboardResource(name) {
	const resource = createDocumentResource({
		doctype: 'Insights Dashboard',
		name: name,
		whitelistedMethods: {
			add_item: 'add_item',
			get_chart_options: 'get_charts',
			refresh_items: 'refresh_items',
			update_layout: 'update_layout',
			remove_item: 'remove_item',
			get_chart_data: 'get_chart_data',
			update_filter: 'update_filter',
			get_all_columns: 'get_all_columns',
			get_columns: 'get_columns',
			update_chart_filters: 'update_chart_filters',
		},
	})
	resource.get.fetch()
	return resource
}
