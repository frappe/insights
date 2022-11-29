import { computed, reactive, watch } from 'vue'
import { safeJSONParse } from '@/utils'
import { createDocumentResource, call, debounce } from 'frappe-ui'
import settings from '@/utils/settings'
import dayjs from '@/utils/dayjs'

export default function useDashboard(dashboardName) {
	const dashboard = fetchDashboard(dashboardName)

	dashboard.editing = false
	dashboard.items = computed(() =>
		dashboard.doc?.items.map((v) => {
			const layout = safeJSONParse(v.layout, {})
			return {
				...v,
				...layout,
			}
		})
	)

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
	dashboard.updateNewChartOptions()

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

	dashboard.refreshItems = debounce(() => {
		dashboard.editingLayout = false
		// reload the dashboard doc
		// to re-render the charts with new data
		dashboard.doc.items = []
		dashboard.reload()
	}, 500)

	dashboard.fetchChartData = (chartID) => {
		const request = fetchData(dashboard.get_chart_data, { chart: chartID })
		const parsedData = computed(() => safeJSONParse(request.data, []))
		return reactive({
			data: parsedData,
			loading: computed(() => request.loading),
		})
	}

	dashboard.fetchQueryColumns = (query) => {
		return fetchData(dashboard.get_columns, { query })
	}

	dashboard.filters = computed(() =>
		dashboard.doc?.items.filter((item) => {
			return item.item_type == 'Filter'
		})
	)

	dashboard.getAllColumns = (query) => {
		// returns all columns from all the tables selected in the query
		dashboard.get_all_columns.submit({ query })
		return computed(() => dashboard.get_all_columns.data?.message || [])
	}

	return dashboard
}

function fetchDashboard(name) {
	const resource = createDocumentResource({
		doctype: 'Insights Dashboard',
		name: name,
		whitelistedMethods: {
			add_item: 'add_item',
			get_chart_options: 'get_charts',
			refresh_items: 'refresh_items',
			refresh_item: 'refresh_item',
			update_layout: 'update_layout',
			remove_item: 'remove_item',
			get_chart_data: 'get_chart_data',
			update_filter: 'update_filter',
			get_all_columns: 'get_all_columns',
			get_columns: 'get_columns',
			update_chart_filters: 'update_chart_filters',
			update_markdown: 'update_markdown',
		},
	})
	resource.get.fetch()
	return resource
}

function fetchData(documentRequest, args) {
	// a generic function to fetch data from the a whitelisted method of a document
	// and return a reactive object
	const state = reactive({
		data: [],
		error: null,
		loading: true,
	})
	documentRequest
		.submit(args)
		.then((res) => {
			state.data = res.message
			state.loading = false
		})
		.catch((err) => {
			state.error = err
			state.loading = false
		})
	return state
}
