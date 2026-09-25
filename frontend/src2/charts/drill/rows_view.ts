// A reader and an author both get the query builder's result pane: its grid,
// sort, find, cursor and export. The server does every read. It runs the rows
// as the chart runs them and as of the card's read, and that only holds inside
// the cut. So each control sends its request by name, and the server answers
// inside the same cut.
//
// This module is therefore one `ResultTable`. The pane asks it for rows, a page,
// a search and a file, and it answers from the server instead of from a query
// document.

import { useDebounceFn } from '@vueuse/core'
import { toast } from 'frappe-ui'
import { computed, reactive, ref } from 'vue'
import type { Filter } from '../../components/filter_picker/filter_picker'
import { getErrorMessage } from '../../helpers'
import { saveExportedFile } from '../../query/export_file'
import { column, emptyResult, formatResultRows, order_by } from '../../query/helpers'
import type { ResultTable } from '../../query/result_table'
import { refusalDetail } from '../../not_permitted'
import { __ } from '../../translation'
import type {
	Operation,
	OrderByArgs,
	QueryResult,
	QueryResultColumn,
} from '../../types/query.types'
import type { DrillLevelData, DrillRowFilter, DrillRowsState, DrillRowsSource } from './drill_stack'

/**
 * What the pane's own controls do not cover: which columns name a document, and
 * the reader's own filters on the rows. The builder's rows pane has these
 * filters, but `ResultTable` does not know about them.
 */
type DrillRowsControls = {
	// the answer on screen, after the reader's own filter, sort and find
	level: DrillLevelData
	recordLinks?: DrillLevelData['record_links']
	filters: Filter[]
	// eslint-disable-next-line no-unused-vars
	setFilters: (own: Filter[]) => void
	// eslint-disable-next-line no-unused-vars
	valuesProvider: (column: QueryResultColumn) => (search: string) => Promise<string[]>
	// eslint-disable-next-line no-unused-vars
	rangeProvider: (column: QueryResultColumn) => Promise<[number, number] | undefined>
}

// The server's page size, `chart_drill.PAGE_SIZE`. The cursor counts rows with
// it, so the two must match, or every page after the first shows wrong row
// numbers.
export const ROWS_PAGE_SIZE = 100

// A find is a round trip, so it waits until the reader stops typing. The input
// updates at once; only the request waits.
const FIND_DELAY = 300

/**
 * `first` is the answer the dialog already holds, so mounting fetches nothing.
 */
export function makeDrillRows(first: DrillLevelData, source: DrillRowsSource) {
	const level = ref<DrillLevelData>(first)
	const filters = ref<Filter[]>([])
	const sort = ref<DrillRowsState['sort']>([])
	const find = ref('')
	const page = ref(1)

	const rules = (own: Filter[]): DrillRowFilter[] =>
		own.map((filter) => ({
			column: filter.column.name,
			operator: filter.operator,
			value: filter.value,
		}))

	// A column's own filter is left out of its value list. The list comes from
	// the rows the filters leave, and this column's filter already narrowed them
	// to its own values, so a second value could not be picked.
	const others = (column: string) =>
		rules(filters.value.filter((filter) => filter.column.name !== column))

	const executing = ref(false)
	const executionError = ref('')
	const downloading = ref(false)

	const state = (): DrillRowsState => ({
		row_filters: rules(filters.value),
		sort: sort.value,
		find: find.value,
		page: page.value,
	})

	// Each read takes a new token. A search typed while a slower one still runs
	// must discard the older answer, or it would show under the newer search.
	let inFlight = 0
	async function read() {
		const token = ++inFlight
		executing.value = true
		executionError.value = ''
		try {
			const answer = await source.read(state())
			if (token !== inFlight) return
			// nothing ran, so there is no page of rows and no count to show. This
			// happens when a permission is removed between two reads of the level.
			if (answer.not_permitted) {
				executionError.value = refusalDetail(
					answer.not_permitted.doctypes,
					__('You do not have access to these rows'),
				)
				return
			}
			level.value = answer
		} catch (error: any) {
			if (token !== inFlight) return
			console.error('[insights] Could not read these rows.', error)
			executionError.value = getErrorMessage(error) || __('Could not read these rows')
		} finally {
			if (token === inFlight) executing.value = false
		}
	}

	// A new filter or sort changes the first page, so staying on page four would
	// show an arbitrary set of rows.
	function reread() {
		page.value = 1
		read()
	}

	const result = computed<QueryResult>(() => {
		const answered: QueryResult = {
			...emptyResult(),
			columns: level.value.columns,
			rows: level.value.rows,
			totalRowCount: level.value.total_row_count || 0,
		}
		// the grid renders the formatted rows, and a cell's link maps back to the
		// raw row through them. These are the cut's source rows, so no column is
		// grouped by a grain
		return { ...answered, formattedRows: formatResultRows(answered, {}) }
	})

	// The grid takes its sort arrows from the operations behind a result, so
	// these are the operations for the current sort. Nothing runs them here: the
	// server builds its own from the same sort list.
	const currentOperations = computed<Operation[]>(() =>
		sort.value.map((rule) =>
			order_by({ column: column(rule.column), direction: rule.direction }),
		),
	)

	function addOrderBy(args: OrderByArgs) {
		const named = args.column.column_name
		const direction = args.direction === 'desc' ? 'desc' : 'asc'
		sort.value = [{ column: named, direction }, ...sort.value.filter((r) => r.column !== named)]
		reread()
	}

	function removeOrderBy(column_name: string) {
		if (!sort.value.some((rule) => rule.column === column_name)) return
		sort.value = sort.value.filter((rule) => rule.column !== column_name)
		reread()
	}

	// The reader's own filters on these rows. They last as long as the level (a
	// new rows level creates a new source), and the clicked card does not get
	// them.
	function setFilters(own: Filter[]) {
		filters.value = own
		reread()
	}

	const askAgain = useDebounceFn(reread, FIND_DELAY)
	function setFind(term: string) {
		if (term === find.value) return
		find.value = term
		askAgain()
	}

	function goToPage(to: number) {
		if (to === page.value) return
		page.value = to
		read()
	}

	let downloads = 0
	function exportRows(format: string, filename: string) {
		const token = ++downloads
		downloading.value = true
		source
			.download(state(), format)
			.then((data: string) => {
				if (token !== downloads) return
				if (!data) {
					toast.warning(__('Download Failed'), {
						description: __('No data found to download.'),
					})
					return
				}
				const saved = saveExportedFile(data, format, filename)
				toast.success(__('Export Successful'), {
					description: __(`File "{0}" exported successfully`, saved),
				})
			})
			.catch((error: any) => {
				if (token !== downloads) return
				toast.error(__('Download Failed'), {
					description: getErrorMessage(error) || __('Failed to download file'),
				})
			})
			.finally(() => {
				if (token === downloads) downloading.value = false
			})
	}

	function cancelDownload() {
		downloads++
		downloading.value = false
	}

	const table: ResultTable & DrillRowsControls = reactive({
		level,
		ready: computed(() => Boolean(level.value.columns.length)),
		executing,
		executionError,
		result,

		currentPage: page,
		pageSize: ROWS_PAGE_SIZE,
		goToPage,
		// the total comes with every answer, so there is nothing more to request
		fetchResultCount: undefined,

		currentOperations,
		addOrderBy,
		removeOrderBy,

		findTerm: find,
		setFind,

		filters,
		setFilters,
		valuesProvider: (column: QueryResultColumn) => (search: string) =>
			source.values(column.name, search, others(column.name)),
		rangeProvider: (column: QueryResultColumn) =>
			source.range(column.name, others(column.name)),

		downloading,
		exportResults: computed(() => (level.value.can_export ? exportRows : undefined)),
		cancelDownload,

		// which columns name a desk document, as the server answered. It is read
		// from the current answer, so it survives a sort, a find and a page change:
		// the cut and its links stay the same
		recordLinks: computed(() => level.value.record_links),
	})

	return table
}
