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
export const column = (column_name: string, options?: ColumnOptions): Column => ({
	type: 'column',
	column_name,
	options,
})
export const operator = (operator: FilterOperator): FilterOperator => operator
export const value = (value: FilterValue): FilterValue => value
export const expression = (expression: string): Expression => ({
	type: 'expression',
	expression,
})

export const window_operation = (options: WindowOperationArgs): WindowOperation => ({
	type: 'window_operation',
	operation: options.operation,
	column: options.column,
	partition_by: options.partition_by,
	order_by: options.order_by,
})

export const pipeline_step_types = {
	source: {
		label: 'Table',
		type: 'source',
		icon: Table,
		color: 'gray',
		class: 'text-gray-600 bg-gray-100',
		init: (args: SourceArgs): Source => ({ type: 'source', ...args }),
		getStepLabel: (step: Source) => step.table.table_name,
	},
	join: {
		label: 'Join',
		type: 'join',
		icon: Merge,
		color: 'gray',
		class: 'text-gray-600 bg-gray-100',
		init: (args: JoinArgs): Join => ({ type: 'join', ...args }),
		getStepLabel: (step: Join) => step.table.table_name,
	},
	select: {
		label: 'Select',
		type: 'select',
		icon: Pointer,
		color: 'gray',
		class: 'text-gray-600 bg-gray-100',
		init: (args: SelectArgs): Select => ({ type: 'select', ...args }),
		getStepLabel: (step: Select) => {
			return `${step.column_names.length} columns`
		},
	},
	remove: {
		label: 'Remove',
		type: 'remove',
		icon: XSquareIcon,
		color: 'gray',
		class: 'text-gray-600 bg-gray-100',
		init: (args: RemoveArgs): Remove => ({ type: 'remove', ...args }),
		getStepLabel: (step: Remove) => {
			if (step.column_names && step.column_names.length > 1) {
				return `Remove ${step.column_names.length} columns`
			}
			if (step.column_names && step.column_names.length === 1) {
				return `Remove ${step.column_names[0]}`
			}
		},
	},
	rename: {
		label: 'Rename',
		type: 'rename',
		icon: TextCursorInput,
		color: 'gray',
		class: 'text-gray-600 bg-gray-100',
		init: (args: RenameArgs): Rename => ({ type: 'rename', ...args }),
		getStepLabel: (step: Rename) => {
			return `${step.column.column_name} -> ${step.new_name}`
		},
	},
	cast: {
		label: 'Cast',
		type: 'cast',
		icon: TextCursorInput,
		color: 'gray',
		class: 'text-gray-600 bg-gray-100',
		init: (args: CastArgs): Cast => ({ type: 'cast', ...args }),
		getStepLabel: (step: Cast) => {
			return `${step.column.column_name} -> ${step.data_type}`
		},
	},
	filter: {
		label: 'Filter',
		type: 'filter',
		icon: Filter,
		color: 'gray',
		class: 'text-gray-600 bg-gray-100',
		init: (args: FilterArgs): Filter => ({ type: 'filter', ...args }),
		getStepLabel: (step: Filter) => {
			// @ts-ignore
			if (step.expression) return step.expression.expression
			// @ts-ignore
			return `${step.column.column_name} ${step.operator} ${step.value}`
		},
	},
	mutate: {
		label: 'Calculate',
		type: 'mutate',
		icon: Sigma,
		color: 'gray',
		class: 'text-gray-600 bg-gray-100',
		init: (args: MutateArgs): Mutate => ({ type: 'mutate', ...args }),
		getStepLabel: (step: Mutate) => {
			return step.label
		},
	},
	summarize: {
		label: 'Summarize',
		type: 'summarize',
		icon: Combine,
		color: 'gray',
		class: 'text-gray-600 bg-gray-100',
		init: (args: SummarizeArgs): Summarize => ({ type: 'summarize', ...args }),
		getStepLabel: (step: Summarize) => {
			return `${Object.keys(step.metrics).join(', ')} BY ${step.by
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
		getStepLabel: (step: PivotWider) => {
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
		getStepLabel: (step: OrderBy) => {
			return `${step.column.column_name} ${step.direction}`
		},
	},
	limit: {
		label: 'Limit',
		type: 'limit',
		icon: Indent,
		color: 'gray',
		class: 'text-gray-600 bg-gray-100',
		init: (limit: number): Limit => ({ type: 'limit', limit }),
		getStepLabel: (step: Limit) => {
			return `Limit ${step.limit}`
		},
	},
}

export const source = pipeline_step_types.source.init
export const join = pipeline_step_types.join.init
export const select = pipeline_step_types.select.init
export const rename = pipeline_step_types.rename.init
export const remove = pipeline_step_types.remove.init
export const cast = pipeline_step_types.cast.init
export const filter = pipeline_step_types.filter.init
export const mutate = pipeline_step_types.mutate.init
export const summarize = pipeline_step_types.summarize.init
export const pivot_wider = pipeline_step_types.pivot_wider.init
export const order_by = pipeline_step_types.order_by.init
export const limit = pipeline_step_types.limit.init
