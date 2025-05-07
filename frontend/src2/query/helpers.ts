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
import { FIELDTYPES, GranularityType } from '../helpers/constants'
import dayjs from '../helpers/dayjs'
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
	Summarize,
	SummarizeArgs,
	Table,
	TableArgs,
	Union,
	UnionArgs,
} from '../types/query.types'

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

export function getFormattedRows(result: QueryResult, operations: Operation[]) {
	if (!result.rows?.length || !result.columns?.length) return []

	const rows = copy(result.rows)
	const columns = copy(result.columns)
	const _operations = copy(operations)
	const summarize_step = _operations.reverse().find((op) => op.type === 'summarize')
	const pivot_step = _operations.reverse().find((op) => op.type === 'pivot_wider')

	const getGranularity = (column_name: string) => {
		const dim =
			summarize_step?.dimensions.find((dim) => dim.dimension_name === column_name) ||
			pivot_step?.rows.find((dim) => dim.dimension_name === column_name)
		return dim ? dim.granularity : null
	}

	const formattedRows = rows.map((row) => {
		const formattedRow = { ...row }
		columns.forEach((column) => {
			if (FIELDTYPES.DATE.includes(column.type) && getGranularity(column.name)) {
				const granularity = getGranularity(column.name) as GranularityType
				formattedRow[column.name] = getFormattedDate(row[column.name], granularity)
			}
		})
		return formattedRow
	})
	return formattedRows
}

export function getFormattedDate(date: string, granularity: GranularityType) {
	if (!date) return ''

	const dayjsFormat: Record<GranularityType, string> = {
		second: 'MMMM D, YYYY h:mm:ss A',
		minute: 'MMMM D, YYYY h:mm A',
		hour: 'MMMM D, YYYY h:00 A',
		day: 'MMMM D, YYYY',
		week: 'MMM Do, YYYY',
		month: 'MMMM, YYYY',
		year: 'YYYY',
		quarter: '[Q]Q, YYYY',
	}

	if (!dayjsFormat[granularity]) return date
	return dayjs(date).format(dayjsFormat[granularity])
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
	const isDate = FIELDTYPES.DATE.includes(column.type)
	return {
		column_name: column.name,
		data_type: column.type as DimensionDataType,
		granularity: isDate ? 'month' : undefined,
		dimension_name: column.name,
	}
}

export const query_operation_types = {
	source: {
		label: 'Source',
		type: 'source',
		icon: DatabaseZap,
		color: 'gray',
		class: 'text-gray-600 bg-gray-100',
		init: (args: SourceArgs): Source => ({ type: 'source', ...args }),
		getDescription: (op: Source) => {
			return op.table.type == 'table' ? `${op.table.table_name}` : `${op.table.query_name}`
		},
	},
	join: {
		label: 'Join',
		type: 'join',
		icon: h(BlendIcon, { class: '-rotate-45' }),
		color: 'gray',
		class: 'text-gray-600 bg-gray-100',
		init: (args: JoinArgs): Join => ({ type: 'join', ...args }),
		getDescription: (op: Join) => {
			return op.table.type == 'table' ? `${op.table.table_name}` : `${op.table.query_name}`
		},
	},
	union: {
		label: 'Union',
		type: 'union',
		icon: BetweenHorizonalStart,
		color: 'gray',
		class: 'text-gray-600 bg-gray-100',
		init: (args: UnionArgs): Union => ({ type: 'union', ...args }),
		getDescription: (op: Union) => {
			return op.table.type == 'table' ? `${op.table.table_name}` : `${op.table.query_name}`
		},
	},
	select: {
		label: 'Select',
		type: 'select',
		icon: ColumnsIcon,
		color: 'gray',
		class: 'text-gray-600 bg-gray-100',
		init: (args: SelectArgs): Select => ({ type: 'select', ...args }),
		getDescription: (op: Select) => {
			return `${op.column_names.length} columns`
		},
	},
	remove: {
		label: 'Remove',
		type: 'remove',
		icon: XSquareIcon,
		color: 'gray',
		class: 'text-gray-600 bg-gray-100',
		init: (args: RemoveArgs): Remove => ({ type: 'remove', ...args }),
		getDescription: (op: Remove) => {
			if (op.column_names.length < 3) {
				return `${op.column_names.join(', ')}`
			}
			return `${op.column_names.length} columns`
		},
	},
	rename: {
		label: 'Rename',
		type: 'rename',
		icon: TextCursorInput,
		color: 'gray',
		class: 'text-gray-600 bg-gray-100',
		init: (args: RenameArgs): Rename => ({ type: 'rename', ...args }),
		getDescription: (op: Rename) => {
			return `${op.column.column_name} -> ${op.new_name}`
		},
	},
	cast: {
		label: 'Cast',
		type: 'cast',
		icon: Repeat,
		color: 'gray',
		class: 'text-gray-600 bg-gray-100',
		init: (args: CastArgs): Cast => ({ type: 'cast', ...args }),
		getDescription: (op: Cast) => {
			return `${op.column.column_name} -> ${op.data_type}`
		},
	},
	filter: {
		label: 'Filter',
		type: 'filter',
		icon: FilterIcon,
		color: 'gray',
		class: 'text-gray-600 bg-gray-100',
		init: (args: FilterArgs): Filter => ({ type: 'filter', ...args }),
		getDescription: (op: Filter) => {
			// @ts-ignore
			if (op.expression) return `custom expression`
			// @ts-ignore
			return `${op.column.column_name}`
		},
	},
	filter_group: {
		label: 'Filter Group',
		type: 'filter_group',
		icon: FilterIcon,
		color: 'gray',
		class: 'text-gray-600 bg-gray-100',
		init: (args: FilterGroupArgs): FilterGroup => ({ type: 'filter_group', ...args }),
		getDescription: (op: FilterGroup) => {
			if (!op.filters.length) return 'empty'
			const columns = op.filters.map((f) => {
				if ('expression' in f) return 'custom expression'
				return f.column.column_name
			})
			const more = columns.length - 2
			return `${columns.slice(0, 2).join(', ')}${more > 0 ? ` & ${more} more` : ''}`
		},
	},
	mutate: {
		label: 'Calculate',
		type: 'mutate',
		icon: FunctionSquare,
		color: 'gray',
		class: 'text-gray-600 bg-gray-100',
		init: (args: MutateArgs): Mutate => ({ type: 'mutate', ...args }),
		getDescription: (op: Mutate) => {
			return `${op.new_name}`
		},
	},
	summarize: {
		label: 'Summarize',
		type: 'summarize',
		icon: Combine,
		color: 'gray',
		class: 'text-gray-600 bg-gray-100',
		init: (args: SummarizeArgs): Summarize => ({ type: 'summarize', ...args }),
		getDescription: (op: Summarize) => {
			const measures = op.measures.map((m) => m.measure_name).join(', ')
			const dimensions = op.dimensions.map((g) => g.column_name).join(', ')
			return `${measures} BY ${dimensions}`
		},
	},
	pivot_wider: {
		label: 'Pivot',
		type: 'pivot_wider',
		icon: GitBranch,
		color: 'gray',
		class: 'text-gray-600 bg-gray-100',
		init: (args: PivotWiderArgs): PivotWider => ({ type: 'pivot_wider', ...args }),
		getDescription: (op: PivotWider) => {
			return 'Pivot Wider'
		},
	},
	order_by: {
		label: 'Sort',
		type: 'order_by',
		icon: ArrowUpDown,
		color: 'gray',
		class: 'text-gray-600 bg-gray-100',
		init: (args: OrderByArgs): OrderBy => ({ type: 'order_by', ...args }),
		getDescription: (op: OrderBy) => {
			return `${op.column.column_name} ${op.direction}`
		},
	},
	limit: {
		label: 'Limit',
		type: 'limit',
		icon: Indent,
		color: 'gray',
		class: 'text-gray-600 bg-gray-100',
		init: (limit: number): Limit => ({ type: 'limit', limit }),
		getDescription: (op: Limit) => {
			return `${op.limit}`
		},
	},
	custom_operation: {
		label: 'Custom Operation',
		type: 'custom_operation',
		icon: Braces,
		color: 'gray',
		class: 'text-gray-600 bg-gray-100',
		init: (args: CustomOperationArgs): CustomOperation => ({ type: 'custom_operation', ...args }),
		getDescription: (op: CustomOperation) => {
			return `${op.expression.expression}`
		},
	},
	sql: {
		label: 'SQL',
		type: 'sql',
		icon: ScrollText,
		color: 'gray',
		class: 'text-gray-600 bg-gray-100',
		init: (args: SQLArgs): SQL => ({ type: 'sql', ...args }),
		getDescription: (op: SQL) => {
			return "SQL"
		},
	},
	code: {
		label: 'Code',
		type: 'code',
		icon: Braces,
		color: 'gray',
		class: 'text-gray-600 bg-gray-100',
		init: (args: CodeArgs): Code => ({ type: 'code', ...args }),
		getDescription: (op: Code) => {
			return "Code"
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
export const summarize = query_operation_types.summarize.init
export const pivot_wider = query_operation_types.pivot_wider.init
export const order_by = query_operation_types.order_by.init
export const limit = query_operation_types.limit.init
export const custom_operation = query_operation_types.custom_operation.init
export const sql = query_operation_types.sql.init
export const code = query_operation_types.code.init
