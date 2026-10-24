import { __ } from '../../translation'
import type { PaginationState } from '../../composables/usePagination'
import type { QueryResult } from '../../types/query.types'

/**
 * What the run cost, for the footer's status line. A `timeTaken` of -1 is the
 * server saying it answered from cache. A result that never ran has nothing to
 * report, so it reports nothing rather than "fetched in 0s".
 */
export function fetchTiming(result: QueryResult): string {
	if (!result.executedSQL) return ''
	if (result.timeTaken === -1) return __('from cache')
	return __('fetched in {0}s', String(Number(result.timeTaken.toFixed(2))))
}

/**
 * The result's row count, when it is known. A last page that ends short of a
 * full one ends the result, so its last row is the count and the server need
 * not be asked for it.
 */
export function knownRowCount(options: {
	totalRowCount?: number
	loadedCount: number
	/** whether the host can ask the server for a count */
	fetchable: boolean
	paging?: Pick<PaginationState, 'isLastPage' | 'to'>
}): number | undefined {
	if (options.totalRowCount) return options.totalRowCount
	if (!options.fetchable) return options.loadedCount
	if (options.paging?.isLastPage.value) return options.paging.to.value
	return undefined
}

export function rowCountText(count: number): string {
	if (count === 1) return __('Showing 1 row')
	return __('Showing {0} rows', count.toLocaleString())
}

/**
 * The range sentence, cut where the count goes. It is translated whole and the
 * count left unfilled, so the control that loads the count stands wherever the
 * language puts the number.
 */
export function rangeAroundCount(from: number, to: number): [string, string] {
	const sentence = __('Showing {0}–{1} of {2} rows', String(from), String(to))
	const [before, after = ''] = sentence.split('{2}')
	return [before.trim(), after.trim()]
}
