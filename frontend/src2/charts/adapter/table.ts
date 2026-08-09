import { column, rawRowOf } from '../../query/helpers'
import type { FormatGroupArgs } from '../../query/components/formatting_utils'
import type { TableChartConfig } from '../../types/chart.types'
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

/** The cell a reader asked for the rows behind. */
export type TableCellEvent = { column: QueryResultColumn; row: QueryResultRow }

export type TableChartProps = {
	title?: string
	columns: QueryResultColumn[]
	/** Formatted for reading: a date prints at the grain it was grouped by. */
	rows: QueryResultRow[]
	/** The next run is in flight over the rows still on screen. */
	loading?: boolean
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
	compactNumbers?: boolean
	enableColorScale?: boolean
	formatGroup?: FormatGroupArgs
	stickyColumns?: string[]
	columnWidths?: Record<string, number>
	textWrap?: Record<string, boolean>
	/** A rate Measure holds a fraction, so the table is told to print it as one. */
	columnFormats?: Record<string, DataFormat>
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

	if (input.executing) props.loading = true
	// The sort is a config edit the server re-derives the query from, so it is
	// offered only where both halves are held.
	if (!input.readonly) {
		props.onSortChange = (column_name, direction) => sortBy(config, column_name, direction)
		props.drillable = true
	}

	if (config.show_filter_row) props.showFilterRow = true
	if (config.show_column_totals) props.showColumnTotals = true
	if (config.show_row_totals) props.showRowTotals = true
	if (config.compact_numbers) props.compactNumbers = true
	if (config.enable_color_scale) props.enableColorScale = true
	if (config.conditional_formatting) props.formatGroup = config.conditional_formatting
	if (config.sticky_columns?.length) props.stickyColumns = config.sticky_columns
	if (config.column_widths) props.columnWidths = config.column_widths
	if (config.text_wrap) props.textWrap = config.text_wrap

	const columnFormats = columnFormatsOf(config)
	if (Object.keys(columnFormats).length) props.columnFormats = columnFormats

	return {
		component: TableChart,
		props,
		drillDown: {
			// The one type drawn from the formatted rows, so the one resolver that
			// crosses back to the raw one a drill-down reads.
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
 */
function sortBy(config: StoredTableConfig, column_name: string, direction: SortDirection) {
	if (!direction) {
		config.order_by = (config.order_by || []).filter(
			(entry) => entry.column.column_name !== column_name,
		)
		return
	}

	const existing = (config.order_by || []).find(
		(entry) => entry.column.column_name === column_name,
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
