import { useQuery } from '@/utils/query'
import { useStorage } from '@vueuse/core'
import { reactive, watch } from 'vue'

export default function useQueryBuilder() {
	const state = reactive({
		queries: [],
		currentQuery: null,
		showNewDialog: false,
	})

	function openQuery(name) {
		if (!name) return
		const existingQuery = state.queries.find((q) => q.name === name)
		if (existingQuery) {
			state.currentQuery = existingQuery
			return
		}
		const query = useQuery(name)
		state.currentQuery = query
		state.queries.push(query)
		state.showNewDialog = false
	}

	function closeQuery(name) {
		const index = state.queries.findIndex((q) => q.name === name)
		if (index === -1) return
		state.queries.splice(index, 1)
		if (state.currentQuery.name === name) {
			state.currentQuery = state.queries[index - 1] || state.queries[0]
		}
	}

	function isActive(query) {
		return state.currentQuery.name === query
	}

	const openQueries = useStorage('insights:openQueries', [])
	watch(
		() => state.queries.length,
		() => {
			const names = state.queries.map((q) => q.name)
			if (names == openQueries.value) return
			openQueries.value = names
		}
	)

	if (openQueries.value.length && !state.queries.length) {
		openQueries.value.forEach((name) => openQuery(name))
	}

	return Object.assign(state, {
		isActive,
		openQuery,
		closeQuery,
	})
}
