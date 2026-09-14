import { computed, ref, watch, toValue, type ComputedRef, type MaybeRefOrGetter } from 'vue'

const DEFAULT_PAGE_SIZE = 100

export type PaginationOptions = {
	rowCount: MaybeRefOrGetter<number>
	pageSize: MaybeRefOrGetter<number>
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
	endIndex: ComputedRef<number>
	rowDisplayOffset: ComputedRef<number>
	prev: () => void
	next: () => void
	goTo: (pageNum: number) => void
}

// One page is one server chunk: `pageSize` is the stride the host fetches with,
// and a page turn is a fetch.
export function usePagination(options: PaginationOptions): PaginationState {
	const config = useConfig(options)
	const cursor = useCursor(options, config)
	const bounds = useBounds(config, cursor)

	const { page, goTo } = cursor

	function prev() {
		if (bounds.isFirstPage.value) return
		goTo(page.value - 1)
	}
	function next() {
		if (bounds.isLastPage.value) return
		goTo(page.value + 1)
	}

	return { ...bounds, prev, next, goTo }
}

function useConfig(options: PaginationOptions) {
	return {
		pageSize: computed(() => toValue(options.pageSize) ?? DEFAULT_PAGE_SIZE),
		rowCount: computed(() => toValue(options.rowCount)),
		total: computed(() => toValue(options.totalRowCount)),
		enabled: computed(() => Boolean(toValue(options.enabled))),
		isServerPaged: computed(() => Boolean(options.onPageChange)),
	}
}

type Config = ReturnType<typeof useConfig>

function useCursor(options: PaginationOptions, config: Config) {
	const page = ref(toValue(options.currentPage) ?? 1)

	const offset = computed(() => (page.value - 1) * config.pageSize.value)

	function load(to: number) {
		if (to < 1 || to === page.value) return
		page.value = to
	}
	function goTo(to: number) {
		if (to < 1) return
		load(to)
		options.onPageChange?.(to)
	}

	watch(
		() => toValue(options.currentPage),
		(current) => current !== undefined && load(current),
	)

	return { page, offset, goTo }
}

type Cursor = ReturnType<typeof useCursor>

// Translates the cursor into the row indices and labels the table/footer render.
function useBounds(config: Config, cursor: Cursor) {
	const { pageSize, rowCount, total, enabled, isServerPaged } = config
	const { page, offset } = cursor

	const endIndex = computed(() =>
		enabled.value ? Math.min(pageSize.value, rowCount.value) : rowCount.value,
	)

	const from = computed(() => offset.value + 1)
	const to = computed(() => offset.value + endIndex.value)
	const rowDisplayOffset = computed(() => offset.value)
	const currentPage = computed(() => page.value)

	const hasNextChunk = computed(() => {
		if (!isServerPaged.value) return false
		return total.value != null ? to.value < total.value : rowCount.value >= pageSize.value
	})
	const isFirstPage = computed(() => page.value <= 1)
	const isLastPage = computed(() => !hasNextChunk.value)
	const isSinglePage = computed(() => isFirstPage.value && isLastPage.value)

	return {
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
