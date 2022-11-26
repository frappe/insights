import { computed, ref, watch } from 'vue'
import { safeJSONParse } from '@/utils'
import { createDocumentResource, call, debounce } from 'frappe-ui'
import settings from '@/utils/settings'
import dayjs from '@/utils/dayjs'

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
		return dashboard.get_chart_options.submit()
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
	dashboard.saveLayout = (layouts) => {
		dashboard.update_layout
			.submit({
				updated_layout: layouts.reduce((acc, v) => {
					acc[v.id] = { x: v.x, y: v.y, w: v.w, h: v.h }
					return acc
				}, {}),
			})
			.then(() => {
				dashboard.editingLayout = false
			})
	}
	dashboard.addItem = (item) => {
		return dashboard.add_item.submit({ item }).then(() => {
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

	dashboard.refreshItems = debounce(async () => {
		dashboard.editingLayout = false
		dashboard.refreshing = true
		// hack: update the charts
		await dashboard.refresh_items.submit()
		// then reload the dashboard doc
		// to re-render the charts with new data
		dashboard.doc.items = []
		await dashboard.reload()
		dashboard.refreshing = false
	}, 500)

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

	if (settings.doc?.auto_refresh_dashboard_in_minutes) {
		watch(
			() => dashboard.doc?.last_updated_on,
			() => {
				const last_updated_on = dayjs(dashboard.doc.last_updated_on)
				const minute_diff = dayjs().diff(last_updated_on, 'minute')

				if (
					!dashboard.doc.last_updated_on ||
					minute_diff > settings.doc.auto_refresh_dashboard_in_minutes
				) {
					dashboard.refreshItems()
				}
			}
		)
	}

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
