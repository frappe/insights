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

export const table = (table_name: string): Table => ({
	type: 'table',
	table_name,
})
export const column = (column_name: string, options = {}): Column => ({
	type: 'column',
	column_name,
	...options,
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

export const query_operation_types = {
	source: {
		label: 'Table',
		type: 'source',
		icon: Table,
		color: 'gray',
		class: 'text-gray-600 bg-gray-100',
		init: (args: SourceArgs): Source => ({ type: 'source', ...args }),
		getLabel: (op: Source) => `Source: ${op.table.table_name}`,
	},
	join: {
		label: 'Join',
		type: 'join',
		icon: Merge,
		color: 'gray',
		class: 'text-gray-600 bg-gray-100',
		init: (args: JoinArgs): Join => ({ type: 'join', ...args }),
		getLabel: (op: Join) => `Merge: ${op.table.table_name}`,
	},
	select: {
		label: 'Select',
		type: 'select',
		icon: Pointer,
		color: 'gray',
		class: 'text-gray-600 bg-gray-100',
		init: (args: SelectArgs): Select => ({ type: 'select', ...args }),
		getLabel: (op: Select) => {
			return `Select: ${op.column_names.length} columns`
		},
	},
	remove: {
		label: 'Remove',
		type: 'remove',
		icon: XSquareIcon,
		color: 'gray',
		class: 'text-gray-600 bg-gray-100',
		init: (args: RemoveArgs): Remove => ({ type: 'remove', ...args }),
		getLabel: (op: Remove) => {
			if (op.column_names.length === 1) {
				return `Remove: ${op.column_names[0]}`
			}
			return `Remove: ${op.column_names.length} columns`
		},
	},
	rename: {
		label: 'Rename',
		type: 'rename',
		icon: TextCursorInput,
		color: 'gray',
		class: 'text-gray-600 bg-gray-100',
		init: (args: RenameArgs): Rename => ({ type: 'rename', ...args }),
		getLabel: (op: Rename) => {
			return `Rename: ${op.column.column_name} -> ${op.new_name}`
		},
	},
	cast: {
		label: 'Cast',
		type: 'cast',
		icon: TextCursorInput,
		color: 'gray',
		class: 'text-gray-600 bg-gray-100',
		init: (args: CastArgs): Cast => ({ type: 'cast', ...args }),
		getLabel: (op: Cast) => {
			return `Change Type: ${op.column.column_name} -> ${op.data_type}`
		},
	},
	filter: {
		label: 'Filter',
		type: 'filter',
		icon: Filter,
		color: 'gray',
		class: 'text-gray-600 bg-gray-100',
		init: (args: FilterArgs): Filter => ({ type: 'filter', ...args }),
		getLabel: (op: Filter) => {
			// @ts-ignore
			if (op.expression) return `Filter: custom expression`
			// @ts-ignore
			return `Filter: ${op.column.column_name}`
		},
	},
	mutate: {
		label: 'Calculate',
		type: 'mutate',
		icon: Sigma,
		color: 'gray',
		class: 'text-gray-600 bg-gray-100',
		init: (args: MutateArgs): Mutate => ({ type: 'mutate', ...args }),
		getLabel: (op: Mutate) => {
			return `Calculate: ${op.new_name}`
		},
	},
	summarize: {
		label: 'Summarize',
		type: 'summarize',
		icon: Combine,
		color: 'gray',
		class: 'text-gray-600 bg-gray-100',
		init: (args: SummarizeArgs): Summarize => ({ type: 'summarize', ...args }),
		getLabel: (op: Summarize) => {
			return `Summarize: ${Object.keys(op.metrics).join(', ')} BY ${op.by
				.map((g) => g.column_name)
				.join(', ')}`
		},
	},
	pivot_wider: {
		label: 'Pivot',
		type: 'pivot_wider',
		icon: GitBranch,
		color: 'gray',
		class: 'text-gray-600 bg-gray-100',
		init: (args: PivotWiderArgs): PivotWider => ({ type: 'pivot_wider', ...args }),
		getLabel: (op: PivotWider) => {
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
		getLabel: (op: OrderBy) => {
			return `Sort: ${op.column.column_name} ${op.direction}`
		},
	},
	limit: {
		label: 'Limit',
		type: 'limit',
		icon: Indent,
		color: 'gray',
		class: 'text-gray-600 bg-gray-100',
		init: (limit: number): Limit => ({ type: 'limit', limit }),
		getLabel: (op: Limit) => {
			return `Limit: ${op.limit}`
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
export const mutate = query_operation_types.mutate.init
export const summarize = query_operation_types.summarize.init
export const pivot_wider = query_operation_types.pivot_wider.init
export const order_by = query_operation_types.order_by.init
export const limit = query_operation_types.limit.init
