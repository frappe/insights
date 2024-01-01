import { areDeeplyEqual, safeJSONParse } from '@/utils'
import widgets from '@/widgets/widgets'
import { createResource } from 'frappe-ui'
import { getLocal, saveLocal } from 'frappe-ui/src/resources/local'
import { reactive } from 'vue'

export default function usePublicDashboard(public_key) {
	const resource = getPublicDashboard(public_key)
	const state = reactive({
		isPublic: true,
		doc: {
			doctype: 'Insights Dashboard',
			name: undefined,
			owner: undefined,
			title: undefined,
			items: [],
		},
		loading: false,
		itemLayouts: [],
		filterStates: {},
		filtersByChart: {},
		refreshCallbacks: [],
	})

	async function reload() {
		state.loading = true
		await resource.fetch()
		state.doc = resource.data
		state.itemLayouts = state.doc.items.map(makeLayoutObject)
		state.loading = false
	}
	reload()

	function getFilterStateKey(item_id) {
		return `filterState-${state.doc.name}-${item_id}`
	}

	async function getFilterState(item_id) {
		if (!state.filterStates[item_id]) {
			state.filterStates[item_id] = await getLocal(getFilterStateKey(item_id))
		}
		return state.filterStates[item_id]
	}

	async function setFilterState(item_id, value) {
		const filterState = value
			? {
					operator: value.operator,
					value: value.value,
			  }
			: undefined
		if (areDeeplyEqual(filterState, state.filterStates[item_id])) return
		saveLocal(getFilterStateKey(item_id), filterState).then(() => {
			state.filterStates[item_id] = filterState
			refreshLinkedCharts(item_id)
		})
	}

	function refreshLinkedCharts(filter_id) {
		state.doc.items.some((item) => {
			if (item.item_id === filter_id) {
				const charts = Object.keys(item.options.links) || []
				charts.forEach((chart) => {
					refreshChartFilters(chart)
				})
				return true
			}
		})
	}

	async function refreshChartFilters(chart_id) {
		const promises = state.doc.items
			.filter((item) => item.item_type === 'Filter')
			.map(async (filter) => {
				const chart_column = filter.options.links?.[chart_id]
				if (!chart_column) return

				const filter_state = await getFilterState(filter.item_id)
				if (!filter_state || !filter_state.value?.value) return
				return {
					label: filter.options.label,
					column: chart_column,
					value: filter_state.value.value,
					operator: filter_state.operator.value,
					column_type: chart_column.type,
				}
			})
		const filters = await Promise.all(promises)
		state.filtersByChart[chart_id] = filters.filter(Boolean)
	}

	async function getChartFilters(chart_id) {
		if (!state.filtersByChart[chart_id]) {
			await refreshChartFilters(chart_id)
		}
		return state.filtersByChart[chart_id]
	}

	async function getChartResults(itemId, queryName) {
		if (!queryName)
			state.doc.items.some((item) => {
				if (item.item_id === itemId) {
					queryName = item.options.query
					return true
				}
			})
		if (!queryName) {
			throw new Error(`Query not found for item ${itemId}`)
		}
		const filters = await getChartFilters(itemId)
		return await resource.fetch_chart_data.submit({
			public_key,
			item_id: itemId,
			query_name: queryName,
			filters,
		})
	}

	function refreshFilter(filter_id) {
		const filter = state.doc.items.find((item) => item.item_id === filter_id)
		Object.keys(filter.options.links).forEach((item_id) => {
			Object.keys(state.queryResults).forEach((key) => {
				if (key.startsWith(`${item_id}-`)) {
					delete state.queryResults[key]
					getChartResults(item_id)
				}
			})
		})
	}

	async function refresh() {
		await reload()
		state.refreshCallbacks.forEach((fn) => fn())
	}

	function onRefresh(fn) {
		state.refreshCallbacks.push(fn)
	}

	function makeLayoutObject(item) {
		return {
			i: parseInt(item.item_id),
			x: item.layout.x || 0,
			y: item.layout.y || 0,
			w: item.layout.w || widgets[item.item_type].defaultWidth,
			h: item.layout.h || widgets[item.item_type].defaultHeight,
		}
	}

	const isChart = (item) => !['Filter', 'Text'].includes(item.item_type)

	return Object.assign(state, {
		reload,
		getChartResults,
		getFilterStateKey,
		getFilterState,
		setFilterState,
		refreshFilter,
		refreshChartFilters,
		refresh,
		onRefresh,
		isChart,
	})
}

function getPublicDashboard(public_key) {
	const resource = createResource({
		url: 'insights.api.public.get_public_dashboard',
		params: { public_key },
		transform(doc) {
			doc.items = doc.items.map(transformItem)
			return doc
		},
	})
	resource.fetch_chart_data = createResource({
		url: 'insights.api.public.get_public_dashboard_chart_data',
	})
	return resource
}

function transformItem(item) {
	item.options = safeJSONParse(item.options, {})
	item.layout = safeJSONParse(item.layout, {})
	return item
}
