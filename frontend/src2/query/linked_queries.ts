import { copy } from '../helpers'
import useQuery from './query'

/**
 * Every query the given query reads from, transitively.
 *
 * A walk of the query graph, not of a workbook: a query names its sources in its
 * own operations. It lives here so the chart and dashboard graph can ask for a
 * query's dependencies without importing the workbook store.
 *
 * Expects the queries to be loaded.
 */
export function getLinkedQueries(query_name: string, _visited: Set<string> = new Set()): string[] {
	if (_visited.has(query_name)) return []
	_visited.add(query_name)

	const query = useQuery(query_name)
	const linkedQueries = new Set<string>()

	if (!query.isloaded) {
		console.log('Operations not loaded yet for query', query_name)
	}

	const operations = copy(query.currentOperations)
	if (query.activeEditIndex > -1) {
		operations.splice(query.activeEditIndex)
	}

	operations.forEach((op) => {
		if ('table' in op && 'type' in op.table && op.table.type === 'query') {
			linkedQueries.add(op.table.query_name)
		}
	})

	linkedQueries.forEach((q) => getLinkedQueries(q, _visited).forEach((q) => linkedQueries.add(q)))

	return Array.from(linkedQueries)
}
