import {
	ArrowUpDown,
	Combine,
	Filter as FilterIcon,
	GitBranch,
	Indent,
	Merge,
	Pointer,
	Sigma,
	Table as TableIcon,
	TextCursorInput,
	XSquareIcon,
} from 'lucide-vue-next'
import { copy } from '../helpers'
import { FIELDTYPES } from '../helpers/constants'
import dayjs from '../helpers/dayjs'
import {
	Cast,
	CastArgs,
	Column,
	CustomOperation,
	CustomOperationArgs,
	Expression,
	Filter,
	FilterArgs,
	FilterGroup,
	FilterGroupArgs,
	FilterOperator,
	FilterValue,
	GranularityType,
	Join,
	JoinArgs,
	Limit,
	Measure,
	Mutate,
	MutateArgs,
	OrderBy,
	OrderByArgs,
	PivotWider,
	PivotWiderArgs,
	QueryTableArgs,
	Remove,
	RemoveArgs,
	Rename,
	RenameArgs,
	Select,
	SelectArgs,
	Source,
	SourceArgs,
	Summarize,
	SummarizeArgs,
	Table,
	TableArgs,
	Union,
	UnionArgs,
} from '../types/query.types'
import { Query } from './query'

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
	measure_name: 'count(*)',
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

export function getFormattedRows(query: Query) {
	const result = query.result

	if (!result.rows?.length || !result.columns?.length) return []

	const rows = copy(result.rows)
	const columns = copy(result.columns)
	const operations = copy(query.doc.operations)
	const summarize_step = operations.reverse().find((op) => op.type === 'summarize')
	const pivot_step = operations.reverse().find((op) => op.type === 'pivot_wider')

	const getGranularity = (column_name: string) => {
		const dim =
			summarize_step?.dimensions.find((dim) => dim.column_name === column_name) ||
			pivot_step?.rows.find((dim) => dim.column_name === column_name)
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

	const dayjsFormat = {
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

export const query_operation_types = {
	source: {
		label: 'Source',
		type: 'source',
		icon: TableIcon,
		color: 'gray',
		class: 'text-gray-600 bg-gray-100',
		init: (args: SourceArgs): Source => ({ type: 'source', ...args }),
		getDescription: (op: Source) => {
			return op.table.type == 'table' ? `${op.table.table_name}` : `${op.table.query_name}`
		},
	},
	join: {
		label: 'Merge',
		type: 'join',
		icon: Merge,
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
		icon: Merge,
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
		icon: Pointer,
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
		icon: TextCursorInput,
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
		icon: Sigma,
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
		icon: Sigma,
		color: 'gray',
		class: 'text-gray-600 bg-gray-100',
		init: (args: CustomOperationArgs): CustomOperation => ({ type: 'custom_operation', ...args }),
		getDescription: (op: CustomOperation) => {
			return `${op.expression.expression}`
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
