import useQuery from '@/query/resources/useQuery'
import sessionStore from '@/stores/sessionStore'
import { areDeeplyEqual, safeJSONParse } from '@/utils'
import { createToast } from '@/utils/toasts'
import widgets from '@/widgets/widgets'
import { createDocumentResource, debounce } from 'frappe-ui'
import { getLocal, saveLocal } from 'frappe-ui/src/resources/local'
import { reactive } from 'vue'

const session = sessionStore()

export default function useDashboard(name) {
	const resource = getDashboardResource(name)
	const state = reactive({
		doc: {
			doctype: 'Insights Dashboard',
			name: undefined,
			owner: undefined,
			title: undefined,
			items: [],
		},
		isOwner: false,
		canShare: false,
		isPrivate: false,
		editing: false,
		loading: false,
		deleting: false,
		currentItem: undefined,
		draggingWidget: undefined,
		sidebar: {
			open: true,
			position: 'right',
		},
		itemLayouts: [],
		filterStates: {},
		filtersByChart: {},
		refreshCallbacks: [],
	})

	async function reload() {
		state.loading = true
		await resource.get.fetch()
		state.doc = resource.doc
		state.itemLayouts = state.doc.items.map(makeLayoutObject)
		state.isOwner = state.doc.owner == session.user.user_id
		state.canShare = state.isOwner || session.user.is_admin
		resource.is_private.fetch().then((res) => (state.isPrivate = res))
		state.loading = false
	}
	reload()

	async function save() {
		if (!state.editing) return
		state.loading = true
		state.doc.items.forEach((item, idx) => (item.idx = idx))
		state.doc.items.forEach(updateItemLayout)
		await resource.setValue.submit(state.doc)
		await reload()
		state.currentItem = undefined
		state.loading = false
		state.editing = false
		window.location.reload()
	}

	async function deleteDashboard() {
		state.deleting = true
		await resource.delete.submit()
		state.deleting = false
	}

	function addItem(item) {
		if (!state.editing) return
		state.doc.items.push(transformItem(item))
		state.itemLayouts.push(getNewLayout(item))
	}

	function updateItemLayout(item) {
		const layout = state.itemLayouts.find((layout) => layout.i === parseInt(item.item_id))
		item.layout = layout || item.layout
	}

	function removeItem(item) {
		if (!state.editing) return
		const item_index = state.doc.items.findIndex((i) => i.item_id === item.item_id)
		state.doc.items.splice(item_index, 1)
		state.itemLayouts.splice(item_index, 1)
		state.currentItem = undefined
	}

	function setCurrentItem(item_id) {
		if (!state.editing) return
		state.currentItem = state.doc.items.find((i) => i.item_id === item_id)
		state.loadCurrentItemQuery(state.currentItem.options.query)
	}

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
				if (filter_state && filter_state.value?.value) {
					return {
						label: filter.options.label,
						column: chart_column,
						value: filter_state.value.value,
						operator: filter_state.operator.value,
						column_type: chart_column.type,
					}
				}

				const default_operator = filter.options.defaultOperator
				const default_value = filter.options.defaultValue
				if (default_operator?.value && default_value?.value) {
					return {
						label: filter.options.label,
						column: chart_column,
						value: default_value.value,
						operator: default_operator.value,
						column_type: chart_column.type,
					}
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
		return resource.fetch_chart_data.submit({
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
		await resource.clear_charts_cache.submit()
		await reload()
		state.refreshCallbacks.forEach((fn) => fn())
	}

	function onRefresh(fn) {
		state.refreshCallbacks.push(fn)
	}

	const updateTitle = debounce(function (title) {
		if (!title || !state.editing) return
		state.doc.title = title
	}, 500)

	function makeLayoutObject(item) {
		return {
			i: parseInt(item.item_id),
			x: item.layout.x || 0,
			y: item.layout.y || 0,
			w: item.layout.w || widgets[item.item_type].defaultWidth,
			h: item.layout.h || widgets[item.item_type].defaultHeight,
		}
	}

	function getNewLayout(item) {
		// get the next available position
		// consider the height and width of the item
		const defaultWidth = widgets[item.item_type].defaultWidth
		const defaultHeight = widgets[item.item_type].defaultHeight
		const initialX = item.initialX
		const initialY = item.initialY
		delete item.initialX
		delete item.initialY
		return {
			i: parseInt(item.item_id),
			x: initialX || 0,
			y: initialY || 0,
			w: defaultWidth,
			h: defaultHeight,
		}
	}

	function togglePublicAccess(isPublic) {
		if (state.doc.is_public === isPublic) return
		resource.setValue.submit({ is_public: isPublic }).then(() => {
			createToast({
				title: 'Dashboard access updated',
				variant: 'success',
			})
			state.doc.is_public = isPublic
		})
	}

	function loadCurrentItemQuery(query) {
		if (!query || !state.currentItem) return
		state.currentItem.query = useQuery(query)
		state.currentItem.query.reload()
	}

	const edit = () => ((state.editing = true), (state.currentItem = undefined))
	const discardChanges = () => (
		(state.editing = false), reload(), (state.currentItem = undefined)
	)
	const toggleSidebar = () => (state.sidebar.open = !state.sidebar.open)
	const setSidebarPosition = (position) => (state.sidebar.position = position)
	const isChart = (item) => !['Filter', 'Text'].includes(item.item_type)
	const resetOptions = (item) => {
		item.options = {
			query: item.options.query,
		}
	}

	return Object.assign(state, {
		reload,
		save,
		addItem,
		removeItem,
		setCurrentItem,
		getChartResults,
		getFilterStateKey,
		getFilterState,
		setFilterState,
		refreshFilter,
		refreshChartFilters,
		edit,
		discardChanges,
		toggleSidebar,
		setSidebarPosition,
		updateTitle,
		deleteDashboard,
		refresh,
		onRefresh,
		isChart,
		togglePublicAccess,
		loadCurrentItemQuery,
		resetOptions,
	})
}

function getDashboardResource(name) {
	return createDocumentResource({
		doctype: 'Insights Dashboard',
		name: name,
		whitelistedMethods: {
			fetch_chart_data: 'fetch_chart_data',
			clear_charts_cache: 'clear_charts_cache',
			is_private: 'is_private',
		},
		transform(doc) {
			doc.items = doc.items.map(transformItem)
			return doc
		},
	})
}

function transformItem(item) {
	item.options = safeJSONParse(item.options, {})
	item.layout = safeJSONParse(item.layout, {})
	return item
}
