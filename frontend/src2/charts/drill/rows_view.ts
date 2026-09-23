// The rows level, as every drill reads it.
//
// A reader and an author get the query builder's result pane — its grid, its
// sort, its find, its cursor and its export — and get it from the server. The
// rows run as the chart declares and on the day its card was read, which only
// holds where the cut is made, so every one of those controls is a question
// asked by name and answered inside the same cut.
//
// What that makes this module is one `ResultTable`: the pane asks a source for
// rows, a page, a term and a file, and this is the source that answers with the
// server instead of with a query document.

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
import type {
	DrillLevelData,
	DrillRowFilter,
	DrillRowsReading,
	DrillRowsSource,
} from './drill_stack'

/**
 * What the pane's own controls do not cover: which columns name a document, and
 * the reader's own filter over the rows — the one control the builder's rows
 * pane has that a `ResultTable` knows nothing about.
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

// The page the server cuts, which is `chart_drill.PAGE_SIZE`. The cursor counts
// with it, so the two have to agree: a client that guessed wrong would report
// the wrong row numbers for every page but the first.
export const ROWS_PAGE_SIZE = 100

// A find is a round trip, so it waits for the reader to stop typing. The term
// itself is not delayed — the box stays live and only the question waits.
const FIND_DELAY = 300

/**
 * The reader's rows level: the answer they are looking at, and the three ways
 * they can ask for another one.
 *
 * `first` is the answer the dialog already holds, so mounting fetches nothing.
 */
export function makeDrillRows(first: DrillLevelData, source: DrillRowsSource) {
	const level = ref<DrillLevelData>(first)
	const filters = ref<Filter[]>([])
	const sort = ref<DrillRowsReading['sort']>([])
	const find = ref('')
	const page = ref(1)

	/** The picker's rules as the wire carries them: a column by name, and a literal. */
	const rules = (own: Filter[]): DrillRowFilter[] =>
		own.map((filter) => ({
			column: filter.column.name,
			operator: filter.operator,
			value: filter.value,
		}))

	// A rule is left out of its own value list, or picking a second value would
	// be impossible: the list is read off the rows the reader's other rules
	// narrowed, and the rule on this column has narrowed them to what it holds.
	const others = (column: string) =>
		rules(filters.value.filter((filter) => filter.column.name !== column))

	const executing = ref(false)
	const executionError = ref('')
	const downloading = ref(false)

	const reading = (): DrillRowsReading => ({
		row_filters: rules(filters.value),
		sort: sort.value,
		find: find.value,
		page: page.value,
	})

	// Every read claims the level: a term typed over a slower one still out has
	// to disown it, or the older answer lands under the newer question.
	let inFlight = 0
	async function read() {
		const token = ++inFlight
		executing.value = true
		executionError.value = ''
		try {
			const answer = await source.read(reading())
			if (token !== inFlight) return
			// nothing ran, so there is no page of rows and no count to report. A
			// grant taken away between two readings of the same level lands here.
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

	// A narrower or differently ordered result is a different first page, and
	// staying on page four of it would show the reader an arbitrary stretch.
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
		// the grid draws the formatted rows, and a cell's link crosses back to the
		// raw one through them. These are the cut's source rows, so no column of
		// them was grouped at a grain
		return { ...answered, formattedRows: formatResultRows(answered, {}) }
	})

	// The sort, as the grid reads it back: the arrows come off the operations a
	// result was produced by, and these are the operations this reading stands
	// for. Nothing runs them here — the server built its own from the same list.
	const currentOperations = computed<Operation[]>(() =>
		sort.value.map((rule) =>
			order_by({ column: column(rule.column), direction: rule.direction }),
		),
	)

	function addOrderBy(args: OrderByArgs) {
		const named = args.column.column_name
		const direction = args.direction === 'desc' ? 'desc' : 'asc'
		// the column just clicked is the one the reader wants the rows run by, and
		// the ones they sorted before it stay on as tiebreaks
		sort.value = [{ column: named, direction }, ...sort.value.filter((r) => r.column !== named)]
		reread()
	}

	function removeOrderBy(column_name: string) {
		if (!sort.value.some((rule) => rule.column === column_name)) return
		sort.value = sort.value.filter((rule) => rule.column !== column_name)
		reread()
	}

	// The reader's own rules over these rows. They last exactly as long as the
	// level does — a new rows level makes a new source — and nothing is carried
	// back to the card that was clicked.
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
			.download(reading(), format)
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
		// the total arrives with every answer, so there is nothing left to ask for
		fetchResultCount: undefined,

		currentOperations,
		addOrderBy,
		removeOrderBy,

		findTerm: find,
		setFind,

		filters,
		setFilters,
		// what a rule on one column may pick from, read off the cut the other
		// rules left — the same question the builder asks its own query
		valuesProvider: (column: QueryResultColumn) => (search: string) =>
			source.values(column.name, search, others(column.name)),
		rangeProvider: (column: QueryResultColumn) =>
			source.range(column.name, others(column.name)),

		downloading,
		// the site decides whether data may leave it as a file, so the control is
		// drawn only where the server said it leads somewhere
		exportResults: computed(() => (level.value.can_export ? exportRows : undefined)),
		cancelDownload,

		// which columns name a desk document, as the server answered it. It is
		// read off the current answer so it survives a sort, a find and a page —
		// the cut is the same cut, and so are its links
		recordLinks: computed(() => level.value.record_links),
	})

	return table
}
