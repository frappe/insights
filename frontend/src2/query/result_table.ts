import type {
	AdhocFilters,
	Operation,
	OrderByArgs,
	QueryResult,
	QueryResultColumn,
	QueryResultRow,
} from '../types/query.types'
import type { Query } from './query'

// What a result table needs from whatever produced the rows.
//
// A query store satisfies the whole of it. A chart read store fills in the rows
// and leaves the authoring half out: a chart's result arrives whole, in one
// response, and re-shaping it is a config edit no card owns. Everything past
// the rows is therefore optional, and the table offers only what it was handed
// — an affordance that was not given is not drawn.
export type ResultTable = {
	// there is something to draw
	ready: boolean
	executing: boolean
	result: QueryResult

	// the query the rows came from, which is what column filters are keyed by
	name?: string

	// paging. Absent means the whole result is on screen already.
	currentPage?: number
	pageSize?: number
	goToPage?: (page: number) => void
	fetchResultCount?: () => Promise<void> | void

	// the operations behind the rows, which is where the sort arrows are read from
	currentOperations?: Operation[]

	adhocFilters?: AdhocFilters

	downloading?: boolean
	exportResults?: (format: string, filename: string) => void
	cancelDownload?: () => void

	renameColumn?: (column_name: string, new_name: string) => void
	addOrderBy?: (args: OrderByArgs) => void
	removeOrderBy?: (column_name: string) => void

	/** `row` is the raw row, not the formatted one the table drew. */
	getDrillDownQuery?: (
		column: QueryResultColumn,
		row: QueryResultRow,
	) => Promise<Query | undefined>
}
