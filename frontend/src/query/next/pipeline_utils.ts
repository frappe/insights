const table = (table_name: string): Table => ({
	type: 'table',
	table_name,
})
const column = (column_name: string, options?: ColumnOptions): Column => ({
	type: 'column',
	column_name,
	options,
})
const operator = (operator: Operator): Operator => operator
const value = (value: string | number | boolean): Value => value
const expression = (expression: string): Expression => ({
	type: 'expression',
	expression,
})

const window_operation = (options: WindowOperationArgs): WindowOperation => ({
	type: 'window_operation',
	operation: options.operation,
	column: options.column,
	partition_by: options.partition_by,
	order_by: options.order_by,
})

const source = (args: SourceArgs): Source => ({ type: 'source', ...args })
const join = (args: JoinArgs): Join => ({ type: 'join', ...args })
const filter = (args: FilterArgs): Filter => ({ type: 'filter', ...args })
const mutate = (args: MutateArgs): Mutate => ({ type: 'mutate', ...args })
const summarize = (args: SummarizeArgs): Summarize => ({ type: 'summarize', ...args })
const order_by = (args: OrderByArgs): OrderBy => ({ type: 'order_by', ...args })
const limit = (limit: number): Limit => ({ type: 'limit', limit })
const pivot_wider = (args: PivotWiderArgs): PivotWider => ({ type: 'pivot_wider', ...args })

export {
	column,
	expression,
	filter,
	join,
	limit,
	mutate,
	operator,
	order_by,
	pivot_wider,
	source,
	summarize,
	table,
	value,
	window_operation,
}
