import { computed, ref, watch, toValue, type Ref, type ComputedRef, type MaybeRefOrGetter } from 'vue'

export type PaginationState = {
	currentPage: Ref<number>
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

export function usePagination(options: {
	rowCount: MaybeRefOrGetter<number>
	pageSize: MaybeRefOrGetter<number>
	totalRowCount?: MaybeRefOrGetter<number | undefined>
	currentPage?: MaybeRefOrGetter<number | undefined>
	onPageChange?: (page: number) => void
	enabled?: MaybeRefOrGetter<boolean>
}): PaginationState {
	const pageSize = computed(() => toValue(options.pageSize) ?? 100)
	const currentPage = ref(toValue(options.currentPage) ?? 1)

	watch(
		() => toValue(options.currentPage),
		(val) => {
			if (val !== undefined) currentPage.value = val
		}
	)

	const isServerPaged = computed(() => Boolean(options.onPageChange))

	const isFirstPage = computed(() => currentPage.value <= 1)
	const isLastPage = computed(() => {
		const total = toValue(options.totalRowCount)
		if (total) return currentPage.value >= Math.ceil(total / pageSize.value)
		return toValue(options.rowCount) < pageSize.value
	})
	const isSinglePage = computed(() => isFirstPage.value && isLastPage.value)

	const from = computed(() => (currentPage.value - 1) * pageSize.value + 1)
	const to = computed(() => from.value + toValue(options.rowCount) - 1)

	const startIndex = computed(() => {
		if (!toValue(options.enabled)) return 0
		if (isServerPaged.value) return 0
		return (currentPage.value - 1) * pageSize.value
	})
	const endIndex = computed(() => {
		const len = toValue(options.rowCount)
		if (!toValue(options.enabled)) return len
		if (isServerPaged.value) return Math.min(pageSize.value, len)
		return Math.min(currentPage.value * pageSize.value, len)
	})

	const rowDisplayOffset = computed(() => (currentPage.value - 1) * pageSize.value)

	function prev() {
		if (isFirstPage.value) return
		currentPage.value--
		options.onPageChange?.(currentPage.value)
	}
	function next() {
		if (isLastPage.value) return
		currentPage.value++
		options.onPageChange?.(currentPage.value)
	}
	function goTo(pageNum: number) {
		currentPage.value = pageNum
		options.onPageChange?.(currentPage.value)
	}

	return {
		currentPage,
		isFirstPage,
		isLastPage,
		isSinglePage,
		from,
		to,
		startIndex,
		endIndex,
		rowDisplayOffset,
		prev,
		next,
		goTo,
	}
}
