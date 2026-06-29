import { computed, ref, watch, toValue, type ComputedRef, type MaybeRefOrGetter } from 'vue'

const DEFAULT_PAGE_SIZE = 100

export type PaginationOptions = {
	rowCount: MaybeRefOrGetter<number>
	pageSize: MaybeRefOrGetter<number>
	displayPageSize?: MaybeRefOrGetter<number>
	totalRowCount?: MaybeRefOrGetter<number | undefined>
	currentPage?: MaybeRefOrGetter<number | undefined>
	onPageChange?: (page: number) => void
	enabled?: MaybeRefOrGetter<boolean>
}

export type PaginationState = {
	currentPage: ComputedRef<number>
	from: ComputedRef<number>
	to: ComputedRef<number>
	isFirstPage: ComputedRef<boolean>
	isLastPage: ComputedRef<boolean>
	isSinglePage: ComputedRef<boolean>
	startIndex: ComputedRef<number>
	endIndex: ComputedRef<number>
	rowDisplayOffset: ComputedRef<number>
	prev: () => void
	next: () => void
	goTo: (pageNum: number) => void
}

// `pageSize` is the server chunk stride; `displayPageSize` is the client slice rendered
// into the DOM. When they differ, a chunk is sub-paginated on the client with no fetch.
export function usePagination(options: PaginationOptions): PaginationState {
	const config = useConfig(options)
	const cursor = useCursor(options, config)
	const bounds = useBounds(config, cursor)

	const { serverPage, clientPage, clientPageCount, lastSubPage, fetchChunk } = cursor

	function prev() {
		if (bounds.isFirstPage.value) return
		if (clientPage.value > 1) clientPage.value--
		else fetchChunk(serverPage.value - 1, lastSubPage.value)
	}
	function next() {
		if (bounds.isLastPage.value) return
		if (clientPage.value < clientPageCount.value) clientPage.value++
		else fetchChunk(serverPage.value + 1)
	}

	return { ...bounds, prev, next, goTo: fetchChunk }
}

function useConfig(options: PaginationOptions) {
	const serverPageSize = computed(() => toValue(options.pageSize) ?? DEFAULT_PAGE_SIZE)
	return {
		serverPageSize,
		displayPageSize: computed(() => toValue(options.displayPageSize) ?? serverPageSize.value),
		rowCount: computed(() => toValue(options.rowCount)),
		total: computed(() => toValue(options.totalRowCount)),
		enabled: computed(() => Boolean(toValue(options.enabled))),
		isServerPaged: computed(() => Boolean(options.onPageChange)),
	}
}

type Config = ReturnType<typeof useConfig>

// Tracks which server chunk is loaded and which sub-page within it is shown.
function useCursor(options: PaginationOptions, config: Config) {
	const serverPage = ref(toValue(options.currentPage) ?? 1)
	const clientPage = ref(1)

	const clientPageCount = computed(() =>
		Math.max(1, Math.ceil(config.rowCount.value / config.displayPageSize.value))
	)
	const chunkOffset = computed(() => (serverPage.value - 1) * config.serverPageSize.value)

	function loadChunk(page: number, subPage = 1) {
		if (page < 1 || page === serverPage.value) return
		serverPage.value = page
		clientPage.value = subPage
	}
	function fetchChunk(page: number, subPage = 1) {
		if (page < 1) return
		loadChunk(page, subPage)
		options.onPageChange?.(page)
	}

	// last sub-page of a full chunk — where a backward chunk hop should land
	const lastSubPage = computed(() =>
		Math.ceil(config.serverPageSize.value / config.displayPageSize.value)
	)

	// follow external page changes; clamp the sub-page when the chunk shrinks
	watch(() => toValue(options.currentPage), (page) => page !== undefined && loadChunk(page))
	watch(clientPageCount, (count) => (clientPage.value = Math.min(clientPage.value, count)))

	return { serverPage, clientPage, clientPageCount, chunkOffset, lastSubPage, fetchChunk }
}

type Cursor = ReturnType<typeof useCursor>

// Translates the cursor into the row indices and labels the table/footer render.
function useBounds(config: Config, cursor: Cursor) {
	const { serverPageSize, displayPageSize, rowCount, total, enabled, isServerPaged } = config
	const { serverPage, clientPage, clientPageCount, chunkOffset } = cursor

	const startIndex = computed(() =>
		enabled.value ? (clientPage.value - 1) * displayPageSize.value : 0
	)
	const endIndex = computed(() =>
		enabled.value
			? Math.min(clientPage.value * displayPageSize.value, rowCount.value)
			: rowCount.value
	)

	const from = computed(() => chunkOffset.value + startIndex.value + 1)
	const to = computed(() => chunkOffset.value + endIndex.value)
	const rowDisplayOffset = computed(() => chunkOffset.value + startIndex.value)
	const currentPage = computed(
		() => Math.floor(chunkOffset.value / displayPageSize.value) + clientPage.value
	)

	const hasNextChunk = computed(() => {
		if (!isServerPaged.value) return false
		return total.value != null ? to.value < total.value : rowCount.value >= serverPageSize.value
	})
	const isFirstPage = computed(() => serverPage.value <= 1 && clientPage.value <= 1)
	const isLastPage = computed(() => clientPage.value >= clientPageCount.value && !hasNextChunk.value)
	const isSinglePage = computed(() => isFirstPage.value && isLastPage.value)

	return {
		startIndex,
		endIndex,
		rowDisplayOffset,
		from,
		to,
		currentPage,
		isFirstPage,
		isLastPage,
		isSinglePage,
	}
}
