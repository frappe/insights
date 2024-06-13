import dayjs from '@/utils/dayjs'
import {
	ArrowUpDown,
	Combine,
	Filter,
	GitBranch,
	Indent,
	Merge,
	Pointer,
	Sigma,
	Table,
	TextCursorInput,
	XSquareIcon,
} from 'lucide-vue-next'

export const table = (data_source: string, table_name: string): Table => ({
	type: 'table',
	data_source,
	table_name,
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
		icon: Table,
		color: 'gray',
		class: 'text-gray-600 bg-gray-100',
		init: (args: SourceArgs): Source => ({ type: 'source', ...args }),
		getDescription: (op: Source) => `${op.table.table_name}`,
	},
	join: {
		label: 'Merge',
		type: 'join',
		icon: Merge,
		color: 'gray',
		class: 'text-gray-600 bg-gray-100',
		init: (args: JoinArgs): Join => ({ type: 'join', ...args }),
		getDescription: (op: Join) => `${op.table.table_name}`,
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
		icon: Filter,
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
		icon: Filter,
		color: 'gray',
		class: 'text-gray-600 bg-gray-100',
		init: (args: FilterGroupArgs): FilterGroup => ({ type: 'filter_group', ...args }),
		getDescription: (op: FilterGroup) => {
			const count = op.filters.length
			return `${count} condition${count > 1 ? 's' : ''}`
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
			const measures = op.measures.map((m) => `${m.aggregation}(${m.column_name})`).join(', ')
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
}

export const source = query_operation_types.source.init
export const join = query_operation_types.join.init
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
