import { ref, watch, computed, Ref, ComputedRef } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { watchDebounced } from '@vueuse/core'

export type UrlPaginationState<T> = {
	searchQuery: Ref<string>
	items: Ref<T[]>
	totalCount: Ref<number | undefined>
	currentPage: ComputedRef<number>
	isLoading: Ref<boolean>
	isError: Ref<boolean>
	refresh: () => void
}

export function useUrlPagination<T>(
	fetchData: (search: string, limit: number, offset: number) => Promise<T[]>,
	fetchCount: (search: string) => Promise<number>,
	pageSize = 100,
	onSuccess?: () => void,
): UrlPaginationState<T> {
	const route = useRoute()
	const router = useRouter()

	const searchQuery = ref((route.query.search as string) || '')
	const items = ref<T[]>([]) as Ref<T[]>
	const totalCount = ref<number | undefined>(undefined)
	const isLoading = ref(false)
	const isError = ref(false)
	const currentPage = computed(() => Number(route.query.page) || 1)
	const refreshTrigger = ref(0)

	function refresh() {
		refreshTrigger.value++
	}

	watchDebounced(
		searchQuery,
		(newSearch) => {
			const currentSearch = (route.query.search as string) || ''
			if (newSearch === currentSearch) return
			router.replace({
				query: { ...route.query, search: newSearch || undefined, page: 1 },
			})
		},
		{ debounce: 300 },
	)

	watch(
		() => ({
			search: route.query.search as string | undefined,
			page: route.query.page as string | undefined,
			_trigger: refreshTrigger.value,
		}),
		async ({ search, page }, oldVal, onCleanup) => {
			let isAborted = false

			onCleanup(() => {
				isAborted = true
			})

			const s = search || ''
			const p = Number(page) || 1
			if (searchQuery.value !== s) searchQuery.value = s

			const offset = (p - 1) * pageSize
			isLoading.value = true
			isError.value = false

			try {
				const [fetchedItems, count] = await Promise.all([
					fetchData(s, pageSize, offset),
					fetchCount(s),
				])

				if (isAborted) return

				items.value = fetchedItems
				totalCount.value = count

				if (count > 0 && offset >= count) {
					router.replace({ query: { ...route.query, page: 1 } })
					return
				}

				onSuccess?.()
			} catch (e) {
				if (isAborted) return
				isError.value = true
			} finally {
				if (!isAborted) isLoading.value = false
			}
		},
		{ immediate: true },
	)

	return { searchQuery, items, totalCount, currentPage, isLoading, isError, refresh }
}
