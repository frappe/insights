import type { InjectionKey, Ref } from 'vue'
import { column, parseFilterString, rawRowOf } from '../../query/helpers'
import type { Filter } from '../../components/filter_picker/filter_picker'
import { FIELDTYPES } from '../../helpers/constants'
import type { FormatGroupArgs } from '../../query/components/formatting_utils'
import type { NumberFormat, TableChartConfig } from '../../types/chart.types'
import { readNumberFormat } from '../number_format'
import { recordUrl } from '../record_link'
import type {
	DataFormat,
	OrderByArgs,
	QueryResultColumn,
	QueryResultRow,
	SortDirection,
	SortOrder,
} from '../../types/query.types'
import TableChart from '../components/TableChart.vue'
import type { ChartAdapterInput, ChartFiller } from './types'

// Table is filler 3: no plot at all. A table maps no value to a visual
// property, so v2's scope rule keeps it out of the library and Insights draws
// the grid — inside the same card, and behind the same states, as every other
// type.
//
// The server has already grouped, pivoted and ordered the rows, so nothing here
// reshapes them. What is left is the display: which of the table's affordances
// this Chart asks for, and which of them this surface may offer at all.

/** The stored config as the table reads it. `order_by` belongs to every Chart. */
type StoredTableConfig = TableChartConfig & { order_by: OrderByArgs[] }

/**
 * The host's find text, read by the grid it narrows. Find is the table's act
 * and client-side over the rows already drawn, so it never reaches the adapter
 * or the server. A host that draws no find box provides nothing and the grid
 * shows every row it was handed.
 */
export const tableFindKey: InjectionKey<Ref<string>> = Symbol('tableFind')

/**
 * The card filter the read holds, written by the grid's filter row.
 *
 * A rule typed in the row is a filter on the card and runs where every other
 * card filter runs — on the server, over the whole result — so the row reports
 * what was typed and the read routes it. Narrowing the drawn rows in the
 * browser read the printed value, and `>1000` against "1,234" is `NaN`.
 *
 * The text is the read's too: the same reset that takes the rules off empties
 * the boxes that wrote them. `ChartBody` provides it from the read it draws, so
 * the row is drawn wherever the config asks for it — a surface that keeps the
 * rules itself, as a dashboard does, takes them off the read instead.
 */
export type TableCardFilter = {
	/** What the boxes hold, one string per column. The row writes into it. */
	text: Readonly<Ref<Record<string, string>>>
	/** The rules the row now states. */
	// eslint-disable-next-line no-unused-vars
	apply: (filters: Filter[]) => void
}

export const tableCardFilterKey: InjectionKey<TableCardFilter> = Symbol('tableCardFilter')

/**
 * The filter row's boxes as rules, for every grid that draws one. The grammar is
 * the result pane's — a comparison where the box opens with one, a substring
 * otherwise — read here once, and against the columns the grid draws so a box
 * left over from a column that went writes no rule.
 *
 * A substring is a rule only a text column has: `contains` runs as `like` on the
 * server, and a date or a boolean has no `like`, so the query threw instead of
 * narrowing. A comparison is a rule only a number column has, for the same
 * reason: `>5` against a string or a date is two types the server cannot
 * compare. Typing prose into such a box states nothing, and states it quietly.
 */
export function cardFilterRules(
	text: Record<string, string>,
	columns: QueryResultColumn[],
): Filter[] {
	const rules: Filter[] = []
	for (const column of columns) {
		const parsed = parseFilterString(text[column.name] || '')
		if (!parsed) continue
		if (parsed.kind === 'numeric') {
			if (FIELDTYPES.NUMBER.includes(column.type)) {
				rules.push({ column, operator: parsed.operator, value: parsed.num })
			}
		} else if (FIELDTYPES.TEXT.includes(column.type)) {
			rules.push({ column, operator: 'contains', value: parsed.text })
		}
	}
	return rules
}

/** The cell a reader asked for the rows behind. */
export type TableCellEvent = { column: QueryResultColumn; row: QueryResultRow }

export type TableChartProps = {
	title?: string
	columns: QueryResultColumn[]
	/** Formatted for reading: a date prints at the grain it was grouped by. */
	rows: QueryResultRow[]
	/** Which way each column is sorted, as the Chart itself is ordered. */
	sortOrder: SortOrder
	/** Absent where the Chart cannot be rewritten, so no arrow is drawn. */
	// eslint-disable-next-line no-unused-vars
	onSortChange?: (column_name: string, direction: SortDirection) => void
	/** Whether a cell may be pointed at for the rows behind it. */
	drillable?: boolean
	showFilterRow?: boolean
	showColumnTotals?: boolean
	showRowTotals?: boolean
	enableColorScale?: boolean
	formatGroup?: FormatGroupArgs
	stickyColumns?: string[]
	columnWidths?: Record<string, number>
	textWrap?: Record<string, boolean>
	/** A rate Measure holds a fraction, so the table is told to print it as one. */
	columnFormats?: Record<string, DataFormat>
	/** How every cell prints, before a column says otherwise. */
	numberFormat?: NumberFormat
	/** How one column prints, by the name of the Measure behind it. */
	numberFormats?: Record<string, NumberFormat>
	/** Where a cell opens its document, for the one column that names one. */
	// eslint-disable-next-line no-unused-vars
	cellLink?: (column: QueryResultColumn, row: QueryResultRow) => string | undefined
}

export function adaptTableChart(input: ChartAdapterInput): ChartFiller | undefined {
	const config = input.config as StoredTableConfig
	const result = input.result
	if (!result.columns.length) return

	const props: TableChartProps = {
		title: input.title,
		columns: result.columns,
		rows: result.formattedRows,
		sortOrder: sortOrderOf(config),
	}

	// The sort is a config edit the server re-derives the query from, so it is
	// offered only where both halves are held. Drilling is not: a reader inspects
	// a cell without changing anything, so every surface whose feed answers a
	// drill offers it.
	if (!input.readonly) {
		props.onSortChange = (column_name, direction) => sortBy(config, column_name, direction)
	}
	if (input.drillable ?? true) props.drillable = true

	if (config.show_filter_row) props.showFilterRow = true
	if (config.show_column_totals) props.showColumnTotals = true
	if (config.show_row_totals) props.showRowTotals = true
	if (config.enable_color_scale) props.enableColorScale = true
	if (config.conditional_formatting) props.formatGroup = config.conditional_formatting
	if (config.sticky_columns?.length) props.stickyColumns = config.sticky_columns
	if (config.column_widths) props.columnWidths = config.column_widths
	if (config.text_wrap) props.textWrap = config.text_wrap

	const columnFormats = columnFormatsOf(config)
	if (Object.keys(columnFormats).length) props.columnFormats = columnFormats

	// The grid formats its own cells, so it is handed the policy rather than a
	// formatter per column: it draws a total row the config names no Measure for.
	const numberFormat = readNumberFormat({ ...config, ...config.number_format })
	if (Object.keys(numberFormat).length) props.numberFormat = numberFormat
	if (config.number_formats) props.numberFormats = config.number_formats

	// A cell of a grid holds a document as often as it holds a value, and only
	// the server can tell which. The link is drawn in the cell itself: a grid has
	// no room for a column of controls, and no row to put one on when the row is
	// a group.
	const links = input.recordLinks
	if (links && Object.keys(links).length) {
		props.cellLink = (column, formattedRow) => {
			const doctype = links[column.name]
			if (!doctype) return
			const row = rawRowOf(result, formattedRow)
			return row ? recordUrl(doctype, row[column.name]) : undefined
		}
	}

	return {
		component: TableChart,
		props,
		drillDown: {
			// The one type drawn from the formatted rows, so the one resolver that
			// crosses back to the raw one a drill reads.
			cellClick: (event: TableCellEvent) => {
				const row = rawRowOf(result, event.row)
				return row ? { column: event.column.name, row } : undefined
			},
		},
	}
}

/** Which way each column is sorted, read off the order the Chart asks for. */
function sortOrderOf(config: StoredTableConfig): SortOrder {
	const order: SortOrder = {}
	for (const entry of config.order_by || []) {
		if (entry?.column?.column_name) order[entry.column.column_name] = entry.direction
	}
	return order
}

/**
 * The one thing a table writes back. It is the same mapping read the other way,
 * so it sits beside it rather than in the component, and it writes to the config
 * it was handed — the Chart's own, which is what makes the next run carry it.
 *
 * The builder's result pane sorts the same config from its own header, so it
 * calls this rather than saying the three branches a second time.
 */
export function sortBy(config: StoredTableConfig, column_name: string, direction: SortDirection) {
	if (!direction) {
		config.order_by = (config.order_by || []).filter(
			(entry) => entry?.column?.column_name !== column_name,
		)
		return
	}

	const existing = (config.order_by || []).find(
		(entry) => entry?.column?.column_name === column_name,
	)
	if (existing) {
		existing.direction = direction
		return
	}
	config.order_by = [...(config.order_by || []), { column: column(column_name), direction }]
}

/** A Measure that carries a unit says so once, and every column of it prints it. */
function columnFormatsOf(config: StoredTableConfig): Record<string, DataFormat> {
	const formats: Record<string, DataFormat> = {}
	for (const measure of config.values || []) {
		if (measure?.measure_name && measure.format) {
			formats[measure.measure_name] = measure.format
		}
	}
	return formats
}
