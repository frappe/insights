import { __ } from '../translation'
import {
	ArrowUpDown,
	BetweenHorizonalStart,
	BlendIcon,
	Braces,
	ColumnsIcon,
	Combine,
	DatabaseZap,
	Filter as FilterIcon,
	FunctionSquare,
	GitBranch,
	Indent,
	Repeat,
	ScrollText,
	TextCursorInput,
	XSquareIcon,
} from 'lucide-vue-next'
import { h } from 'vue'
import { copy } from '../helpers'
import { FIELDTYPES, getDefaultGranularity, GranularityType } from '../helpers/constants'
import dayjs from '../helpers/dayjs'
import useSettings from '../settings/settings'
import {
	Cast,
	CastArgs,
	Code,
	CodeArgs,
	Column,
	CustomOperation,
	CustomOperationArgs,
	Dimension,
	DimensionDataType,
	Expression,
	Filter,
	FilterArgs,
	FilterGroup,
	FilterGroupArgs,
	FilterOperator,
	FilterValue,
	Join,
	JoinArgs,
	Limit,
	Measure,
	MeasureDataType,
	Mutate,
	MutateArgs,
	Operation,
	OrderBy,
	OrderByArgs,
	PivotWider,
	PivotWiderArgs,
	QueryResult,
	QueryResultColumn,
	QueryResultRow,
	QueryTableArgs,
	Remove,
	RemoveArgs,
	Rename,
	RenameArgs,
	Select,
	SelectArgs,
	Source,
	SourceArgs,
	SQL,
	SQLArgs,
	SQLColumn,
	SQLColumnArgs,
	Summarize,
	SummarizeArgs,
	Table,
	TableArgs,
	Union,
	UnionArgs,
} from '../types/query.types'
import session from '../session'

export const table = (args: Partial<TableArgs>): Table => ({
	type: 'table',
	table_name: args.table_name || '',
	data_source: args.data_source || '',
})
export const query_table = (args: Partial<QueryTableArgs>): Table => ({
	type: 'query',
	workbook: args.workbook || '',
	query_name: args.query_name || '',
})
export const column = (column_name: string, options = {}): Column => ({
	type: 'column',
	column_name,
	...options,
})
export const count = (): Measure => ({
	column_name: 'count',
	data_type: 'Integer',
	aggregation: 'count',
	measure_name: 'count_of_rows',
})
export const operator = (operator: FilterOperator): FilterOperator => operator
export const value = (value: FilterValue): FilterValue => value
export const expression = (expression: string): Expression => ({
	type: 'expression',
	expression,
})

// export const window_operation = (options: WindowOperationArgs): WindowOperation => ({
// 	type: 'window_operation',
// 	operation: options.operation,
// 	column: options.column,
// 	partition_by: options.partition_by,
// 	order_by: options.order_by,
// })

// Here rather than in the query store: the island renders a result without ever
// building a query, and importing the store for a blank one pulls the whole
// execution path — socket, queue, autosave — into the island bundle.
export const EMPTY_RESULT: QueryResult = {
	executedSQL: '',
	totalRowCount: 0,
	rows: [],
	formattedRows: [],
	columns: [],
	columnOptions: [],
	timeTaken: 0,
	lastExecutedAt: new Date(),
}

export function getFormattedRows(result: QueryResult, operations: Operation[]) {
	return formatResultRows(result, getColumnGranularity(operations))
}

// The grain a date column was grouped by, per column. A viewer never receives
// the operations, so the server sends it this map instead — same shape, so the
// formatting below stays one implementation.
export function getColumnGranularity(operations: Operation[]) {
	const _operations = copy(operations)
	const summarize_step = _operations.reverse().find((op) => op.type === 'summarize')
	const pivot_step = _operations.reverse().find((op) => op.type === 'pivot_wider')

	const granularity: Record<string, string> = {}
	const dimensions = [...(summarize_step?.dimensions || []), ...(pivot_step?.rows || [])]
	dimensions.forEach((dim) => {
		if (dim.granularity && !granularity[dim.dimension_name]) {
			granularity[dim.dimension_name] = dim.granularity
		}
	})
	return granularity
}

export function formatResultRows(result: QueryResult, granularityByColumn: Record<string, string>) {
	if (!result.rows?.length || !result.columns?.length) return []

	const rows = copy(result.rows)
	const columns = copy(result.columns)
	const getGranularity = (column_name: string) => granularityByColumn[column_name] || null

	const formattedRows = rows.map((row) => {
		const formattedRow = { ...row }
		columns.forEach((column) => {
			if (FIELDTYPES.DATE.includes(column.type) && getGranularity(column.name)) {
				const granularity = getGranularity(column.name) as GranularityType
				formattedRow[column.name] = getFormattedDate(row[column.name], granularity)
			}

			if (
				FIELDTYPES.TEXT.includes(column.type) &&
				typeof row[column.name] === 'string' &&
				row[column.name]
			) {
				const htmlTagRegex = /<[^>]*>/g
				if (htmlTagRegex.test(row[column.name])) {
					htmlTagRegex.lastIndex = 0
					formattedRow[column.name] = row[column.name]
						.replace(htmlTagRegex, '')
						.replace(/\s+/g, ' ')
						.trim()
				}
			}
		})
		return formattedRow
	})
	return formattedRows
}
/**
 * The row `formatResultRows` produced this one from. A surface that draws the
 * formatted rows — a table — reports the row it drew, and everything downstream
 * of a click reads the raw values, so the crossing happens once, here.
 *
 * The two are parallel arrays, so the raw row is the formatted one's position.
 * A row from anywhere else has no position, which is a caller bug rather than a
 * click on nothing: it says so instead of returning quietly.
 */
export function rawRowOf(
	result: QueryResult,
	formattedRow: QueryResultRow,
): QueryResultRow | undefined {
	const index = result.formattedRows.indexOf(formattedRow)
	const row = index === -1 ? undefined : result.rows[index]
	if (!row) {
		console.warn('[insights] No result row behind the row that was clicked.', formattedRow)
	}
	return row
}

/** How a date reads in a cell, a tooltip or a header — spelled out in full. */
const LONG_DATE_FORMATS: Record<string, string> = {
	second: 'MMMM D, YYYY h:mm:ss A',
	minute: 'MMMM D, YYYY h:mm A',
	hour: 'MMMM D, YYYY h:00 A',
	day: 'MMMM D, YYYY',
	week: 'MMM Do, YYYY',
	month: 'MMMM, YYYY',
	year: 'YYYY',
	quarter: '[Q]Q, YYYY',
}

/**
 * How the same date reads on an axis. A category axis draws a label per column,
 * so a spelled-out month is dropped by the overlap rule and the reader is left
 * with a bare grid. Everything is abbreviated, and the year is kept: a category
 * carries no neighbours to read it against.
 */
const AXIS_DATE_FORMATS: Record<string, string> = {
	second: 'MMM D, YYYY h:mm:ss A',
	minute: 'MMM D, YYYY h:mm A',
	hour: 'MMM D, YYYY h A',
	day: 'MMM D, YYYY',
	week: 'MMM D, YYYY',
	month: 'MMM YYYY',
	year: 'YYYY',
	quarter: '[Q]Q YYYY',
}

export function getFormattedDate(date: string, granularity: string) {
	return formatDateBy(date, granularity, LONG_DATE_FORMATS)
}

/** `getFormattedDate`, abbreviated for an axis tick. */
export function getAxisDate(date: string, granularity: string) {
	return formatDateBy(date, granularity, AXIS_DATE_FORMATS)
}

function formatDateBy(date: string, granularity: string, formats: Record<string, string>) {
	if (!date) return ''

	const isTimeOnlyValue = /^\d{1,2}:\d{2}(:\d{2}(\.\d+)?)?$/.test(date)
	if (isTimeOnlyValue) {
		const timeFormats: Record<string, string> = {
			second: 'h:mm:ss A',
			minute: 'h:mm A',
			hour: 'h:00 A',
		}

		if (!timeFormats[granularity]) return date

		const parsed = dayjs(date, ['HH:mm:ss.SSSSSS', 'HH:mm:ss', 'HH:mm'], true)
		return parsed.isValid() ? parsed.format(timeFormats[granularity]) : date
	}

	if (granularity === 'fiscal_year') {
		const d = dayjs(date)
		const fiscalYearStart = session.user.fiscal_year_start
		const fiscalStartMonth = dayjs(fiscalYearStart).month()
		const fiscalStartDay = dayjs(fiscalYearStart).date()

		const fiscalStartThisYear = d.month(fiscalStartMonth).date(fiscalStartDay)
		const startYear = d.isBefore(fiscalStartThisYear) ? d.year() - 1 : d.year()
		const endYear = startYear + 1

		return `FY ${startYear}-${String(endYear).slice(-2)}`
	}

	if (!formats[granularity]) return date
	return dayjs(date).format(formats[granularity])
}

export function getMeasures(columns: QueryResultColumn[]): Measure[] {
	if (!columns?.length) return []
	const count_measure = count()
	return [
		count_measure,
		...columns.filter((column) => FIELDTYPES.MEASURE.includes(column.type)).map(makeMeasure),
	]
}

export function makeMeasure(column: QueryResultColumn): Measure {
	return {
		aggregation: 'sum',
		column_name: column.name,
		measure_name: `sum_of_${column.name}`,
		data_type: column.type as MeasureDataType,
	}
}

export function getDimensions(columns: QueryResultColumn[]): Dimension[] {
	if (!columns?.length) return []
	return columns.filter((column) => FIELDTYPES.DIMENSION.includes(column.type)).map(makeDimension)
}

export function makeDimension(column: QueryResultColumn): Dimension {
	return {
		column_name: column.name,
		data_type: column.type as DimensionDataType,
		granularity: getDefaultGranularity(column.type),
		dimension_name: column.name,
	}
}

export const query_operation_types = {
	source: {
		label: __('Source'),
		type: 'source',
		icon: DatabaseZap,
		color: 'gray',
		class: 'text-ink-gray-5 bg-surface-gray-2',
		init: (args: SourceArgs): Source => ({ type: 'source', ...args }),
		getDescription: (op: Source) => {
			return op.table.type == 'table' ? `${op.table.table_name}` : `${op.table.query_name}`
		},
	},
	join: {
		label: __('Join'),
		type: 'join',
		icon: h(BlendIcon, { class: '-rotate-45' }),
		color: 'gray',
		class: 'text-ink-gray-5 bg-surface-gray-2',
		init: (args: JoinArgs): Join => ({ type: 'join', ...args }),
		getDescription: (op: Join) => {
			return op.table.type == 'table' ? `${op.table.table_name}` : `${op.table.query_name}`
		},
	},
	union: {
		label: __('Union'),
		type: 'union',
		icon: BetweenHorizonalStart,
		color: 'gray',
		class: 'text-ink-gray-5 bg-surface-gray-2',
		init: (args: UnionArgs): Union => ({ type: 'union', ...args }),
		getDescription: (op: Union) => {
			return op.table.type == 'table' ? `${op.table.table_name}` : `${op.table.query_name}`
		},
	},
	select: {
		label: __('Select'),
		type: 'select',
		icon: ColumnsIcon,
		color: 'gray',
		class: 'text-ink-gray-5 bg-surface-gray-2',
		init: (args: SelectArgs): Select => ({ type: 'select', ...args }),
		getDescription: (op: Select) => {
			return `${op.column_names.length} columns`
		},
	},
	remove: {
		label: __('Remove'),
		type: 'remove',
		icon: XSquareIcon,
		color: 'gray',
		class: 'text-ink-gray-5 bg-surface-gray-2',
		init: (args: RemoveArgs): Remove => ({ type: 'remove', ...args }),
		getDescription: (op: Remove) => {
			if (op.column_names.length < 3) {
				return `${op.column_names.join(', ')}`
			}
			return `${op.column_names.length} columns`
		},
	},
	rename: {
		label: __('Rename'),
		type: 'rename',
		icon: TextCursorInput,
		color: 'gray',
		class: 'text-ink-gray-5 bg-surface-gray-2',
		init: (args: RenameArgs): Rename => ({ type: 'rename', ...args }),
		getDescription: (op: Rename) => {
			return `${op.column.column_name} -> ${op.new_name}`
		},
	},
	cast: {
		label: __('Cast'),
		type: 'cast',
		icon: Repeat,
		color: 'gray',
		class: 'text-ink-gray-5 bg-surface-gray-2',
		init: (args: CastArgs): Cast => ({ type: 'cast', ...args }),
		getDescription: (op: Cast) => {
			return `${op.column.column_name} -> ${op.data_type}`
		},
	},
	filter: {
		label: __('Filter'),
		type: 'filter',
		icon: FilterIcon,
		color: 'gray',
		class: 'text-ink-gray-5 bg-surface-gray-2',
		init: (args: FilterArgs): Filter => ({ type: 'filter', ...args }),
		getDescription: (op: Filter) => {
			// @ts-ignore
			if (op.expression) return __('custom expression')
			// @ts-ignore
			return `${op.column.column_name}`
		},
	},
	filter_group: {
		label: __('Filter Group'),
		type: 'filter_group',
		icon: FilterIcon,
		color: 'gray',
		class: 'text-ink-gray-5 bg-surface-gray-2',
		init: (args: FilterGroupArgs): FilterGroup => ({ type: 'filter_group', ...args }),
		getDescription: (op: FilterGroup) => {
			if (!op.filters.length) return __('empty')
			const columns = op.filters.map((f) => {
				if ('expression' in f) return __('custom expression')
				return f.column.column_name
			})
			const more = columns.length - 2
			return `${columns.slice(0, 2).join(', ')}${more > 0 ? ` & ${more} more` : ''}`
		},
	},
	mutate: {
		label: __('Calculate'),
		type: 'mutate',
		icon: FunctionSquare,
		color: 'gray',
		class: 'text-ink-gray-5 bg-surface-gray-2',
		init: (args: MutateArgs): Mutate => ({ type: 'mutate', ...args }),
		getDescription: (op: Mutate) => {
			return `${op.new_name}`
		},
	},
	// No popover entry: the v2 migrator is the only writer.
	sql_column: {
		label: __('SQL column (from v2)'),
		type: 'sql_column',
		icon: ScrollText,
		color: 'gray',
		class: 'text-ink-gray-5 bg-surface-gray-2',
		init: (args: SQLColumnArgs): SQLColumn => ({ type: 'sql_column', ...args }),
		getDescription: (op: SQLColumn) => {
			return `${op.new_name}`
		},
	},
	summarize: {
		label: __('Summarize'),
		type: 'summarize',
		icon: Combine,
		color: 'gray',
		class: 'text-ink-gray-5 bg-surface-gray-2',
		init: (args: SummarizeArgs): Summarize => ({ type: 'summarize', ...args }),
		getDescription: (op: Summarize) => {
			const measures = op.measures.map((m) => m.measure_name).join(', ')
			const dimensions = op.dimensions.map((g) => g.column_name).join(', ')
			return __(`{0} BY {1}`, measures, dimensions)
		},
	},
	pivot_wider: {
		label: __('Pivot'),
		type: 'pivot_wider',
		icon: GitBranch,
		color: 'gray',
		class: 'text-ink-gray-5 bg-surface-gray-2',
		init: (args: PivotWiderArgs): PivotWider => ({ type: 'pivot_wider', ...args }),
		getDescription: (op: PivotWider) => {
			return __('Pivot Wider')
		},
	},
	order_by: {
		label: __('Sort'),
		type: 'order_by',
		icon: ArrowUpDown,
		color: 'gray',
		class: 'text-ink-gray-5 bg-surface-gray-2',
		init: (args: OrderByArgs): OrderBy => ({ type: 'order_by', ...args }),
		getDescription: (op: OrderBy) => {
			return `${op.column.column_name} ${op.direction}`
		},
	},
	limit: {
		label: __('Limit'),
		type: 'limit',
		icon: Indent,
		color: 'gray',
		class: 'text-ink-gray-5 bg-surface-gray-2',
		init: (limit: number): Limit => ({ type: 'limit', limit }),
		getDescription: (op: Limit) => {
			return `${op.limit}`
		},
	},
	custom_operation: {
		label: __('Custom Operation'),
		type: 'custom_operation',
		icon: Braces,
		color: 'gray',
		class: 'text-ink-gray-5 bg-surface-gray-2',
		init: (args: CustomOperationArgs): CustomOperation => ({
			type: 'custom_operation',
			...args,
		}),
		getDescription: (op: CustomOperation) => {
			return `${op.expression.expression}`
		},
	},
	sql: {
		label: __('SQL'),
		type: 'sql',
		icon: ScrollText,
		color: 'gray',
		class: 'text-ink-gray-5 bg-surface-gray-2',
		init: (args: SQLArgs): SQL => ({ type: 'sql', ...args }),
		getDescription: (op: SQL) => {
			return __('SQL')
		},
	},
	code: {
		label: __('Code'),
		type: 'code',
		icon: Braces,
		color: 'gray',
		class: 'text-ink-gray-5 bg-surface-gray-2',
		init: (args: CodeArgs): Code => ({ type: 'code', ...args }),
		getDescription: (op: Code) => {
			return __('Code')
		},
	},
}

export const source = query_operation_types.source.init
export const join = query_operation_types.join.init
export const union = query_operation_types.union.init
export const select = query_operation_types.select.init
export const rename = query_operation_types.rename.init
export const remove = query_operation_types.remove.init
export const cast = query_operation_types.cast.init
export const filter = query_operation_types.filter.init
export const filter_group = query_operation_types.filter_group.init
export const mutate = query_operation_types.mutate.init
export const sql_column = query_operation_types.sql_column.init
export const summarize = query_operation_types.summarize.init
export const pivot_wider = query_operation_types.pivot_wider.init
export const order_by = query_operation_types.order_by.init
export const limit = query_operation_types.limit.init
export const custom_operation = query_operation_types.custom_operation.init
export const sql = query_operation_types.sql.init
export const code = query_operation_types.code.init

// ─── Inline column filter utilities ──────────────────────────────────────────

// Operators checked longest-first so ">=" is not mistaken for ">"
const NUMERIC_OPERATORS = ['>=', '<=', '!=', '>', '<', '='] as const
export type NumericOperator = (typeof NUMERIC_OPERATORS)[number]

export type ParsedFilter =
	| { kind: 'numeric'; operator: NumericOperator; num: number }
	| { kind: 'text'; text: string }

/**
 * Parse a raw filter string (e.g. ">= 100", "foo") into a structured form.
 * Returns null when the string is empty or the numeric part cannot be parsed.
 */
export function parseFilterString(filterStr: string): ParsedFilter | null {
	if (!filterStr) return null

	const op = NUMERIC_OPERATORS.find((o) => filterStr.startsWith(o))
	if (op) {
		const rest = filterStr.slice(op.length).trim()
		const num = Number(rest)
		if (rest === '' || isNaN(num)) return null
		return { kind: 'numeric', operator: op, num }
	}

	return { kind: 'text', text: filterStr }
}

/**
 * Test whether a single cell value matches a parsed filter.
 * Used for client-side (in-memory) filtering.
 */
export function matchesFilter(value: any, parsed: ParsedFilter): boolean {
	if (parsed.kind === 'numeric') {
		const num = Number(value)
		switch (parsed.operator) {
			case '>':
				return num > parsed.num
			case '<':
				return num < parsed.num
			case '>=':
				return num >= parsed.num
			case '<=':
				return num <= parsed.num
			case '=':
				return num === parsed.num
			case '!=':
				return num !== parsed.num
		}
	}
	// text: case-insensitive substring match
	return String(value ?? '')
		.toLowerCase()
		.includes(parsed.text.toLowerCase())
}
