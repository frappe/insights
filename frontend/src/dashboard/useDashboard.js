import widgets from '@/dashboard/widgets/widgets'
import { useQuery } from '@/query/useQueries'
import { safeJSONParse } from '@/utils'
import auth from '@/utils/auth'
import { getFormattedResult } from '@/utils/query/results'
import { createDocumentResource } from 'frappe-ui'
import { getLocal } from 'frappe-ui/src/resources/local'
import { computed, reactive } from 'vue'

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
		editing: false,
		loading: false,
		deleting: false,
		currentItem: undefined,
		draggingWidget: undefined,
		sidebar: {
			open: true,
			position: 'right',
		},
		queries: {},
		queryResults: {},
		itemLayouts: [],
	})

	async function reload() {
		state.loading = true
		await resource.get.fetch()
		state.doc = resource.doc
		state.itemLayouts = state.doc.items.map(makeLayoutObject)
		state.isOwner = state.doc.owner == auth.user.user_id
		state.canShare = state.isOwner || auth.user.is_admin
		state.loading = false
	}
	reload()

	async function save() {
		if (!state.editing) return
		state.loading = true
		state.doc.items.forEach((item, idx) => (item.idx = idx))
		state.doc.items.forEach(updateItemLayout)
		await resource.setValue.submit(state.doc)
		state.currentItem = undefined
		state.loading = false
		state.editing = false
		reload()
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
	}

	function loadQuery(queryName) {
		if (!state.queries[queryName]) {
			state.queries = Object.assign(state.queries, {
				[queryName]: useQuery(queryName),
			})
		}
		return state.queries[queryName]
	}

	async function loadQueryResult(itemId, queryName) {
		if (!queryName)
			state.doc.items.some((item) => {
				if (item.item_id === itemId) {
					queryName = item.options.query
					return true
				}
			})
		if (!queryName) return
		if (state.queryResults[`${itemId}-${queryName}`]) return

		setItemLoading(itemId, true)
		const query = state.loadQuery(queryName)
		const columns = computed(() => query.doc?.columns)
		const filters = await getChartFilters(itemId)
		const res = await resource.fetch_chart_data.submit({
			item_id: itemId,
			query_name: queryName,
			filters,
		})
		const results = getFormattedResult(res.message || [], columns.value)
		state.queryResults = Object.assign(state.queryResults, {
			[`${itemId}-${queryName}`]: results,
		})
		setItemLoading(itemId, false)
	}

	async function getChartFilters(chart_id) {
		const promises = state.doc.items
			.filter((item) => item.item_type === 'Filter')
			.map(async (item) => {
				const chart_column = item.options.links?.[chart_id]
				if (!chart_column) return

				const filter_state = await getLocal(`filterState-${state.doc.name}-${item.item_id}`)
				if (!filter_state || !filter_state.value?.value) return
				return {
					label: item.options.label,
					column: chart_column,
					value: filter_state.value.value,
					operator: filter_state.operator.value,
					column_type: chart_column.type,
				}
			})
		const filters = await Promise.all(promises)
		return filters.filter(Boolean)
	}

	function refreshFilter(filter_id) {
		const filter = state.doc.items.find((item) => item.item_id === filter_id)
		Object.keys(filter.options.links).forEach((item_id) => {
			Object.keys(state.queryResults).forEach((key) => {
				if (key.startsWith(`${item_id}-`)) {
					delete state.queryResults[key]
					loadQueryResult(item_id)
				}
			})
		})
	}

	async function refresh() {
		state.queryResults = {}
		await resource.clear_charts_cache.submit()
		state.doc.items.forEach((item) => loadQueryResult(item.item_id))
	}

	async function updateTitle(title) {
		if (!title || !state.editing) return
		resource.setValue.submit({ title }).then(() => {
			$notify({
				title: 'Dashboard title updated',
				appearance: 'success',
			})
			state.doc.title = title
		})
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

	const edit = () => ((state.editing = true), (state.currentItem = undefined))
	const cancelEdit = () => ((state.editing = false), reload(), (state.currentItem = undefined))
	const toggleSidebar = () => (state.sidebar.open = !state.sidebar.open)
	const setSidebarPosition = (position) => (state.sidebar.position = position)

	const setItemLoading = (item_id, loading) => {
		state.doc.items.some((item) => {
			if (item.item_id === item_id) {
				item.refreshing = loading
				return true
			}
		})
	}

	return Object.assign(state, {
		reload,
		save,
		addItem,
		removeItem,
		setCurrentItem,
		loadQuery,
		loadQueryResult,
		refreshFilter,
		getChartFilters,
		edit,
		cancelEdit,
		toggleSidebar,
		setSidebarPosition,
		updateTitle,
		deleteDashboard,
		refresh,
	})
}

function getDashboardResource(name) {
	return createDocumentResource({
		doctype: 'Insights Dashboard',
		name: name,
		whitelistedMethods: {
			savestate: 'savestate',
			fetch_chart_data: 'fetch_chart_data',
			clear_charts_cache: 'clear_charts_cache',
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
