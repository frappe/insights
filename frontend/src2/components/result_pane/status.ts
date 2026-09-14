import { __ } from '../../translation'
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
