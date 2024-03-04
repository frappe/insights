type Table = {
	type: 'table'
	table_name: string
}
type Column = {
	type: 'column'
	column_name: string
	options?: ColumnOptions
}

type ColumnOptions = {
	date_format?: string
	aggregate?: string
}
type Operator = '==' | '!=' | '>' | '>=' | '<' | '<='
type Value = string | number | boolean
type Expression = {
	type: 'expression'
	expression: string
}

type SourceArgs = { table: Table }
type Source = { type: 'source' } & SourceArgs

type FilterArgs = { column: Column; operator: Operator; value: Value | Column }
type Filter = { type: 'filter' } & FilterArgs

type JoinArgs = { table: Table; left_column: Column; right_column: Column }
type Join = { type: 'join' } & JoinArgs

type Mutation = Column | Expression | WindowOperation
type MutateArgs = { label: string; mutation: Mutation }
type Mutate = { type: 'mutate' } & MutateArgs

type SummarizeArgs = { metrics: Record<string, Column | Expression>; by: Column[] }
type Summarize = { type: 'summarize' } & SummarizeArgs

type OrderByArgs = { direction: 'asc' | 'desc'; column: Column }
type OrderBy = { type: 'order_by' } & OrderByArgs

type Limit = {
	type: 'limit'
	limit: number
}

type WindowOperationType = 'sum' | 'lag_difference' | 'row_number'
type WindowOperationArgs = {
	operation: WindowOperationType
	column: Column
	partition_by?: Column
	order_by?: Column
}
type WindowOperation = { type: 'window_operation' } & WindowOperationArgs

type PivotWiderArgs = {
	id_cols: Column
	names_from: Column
	values_from: Column
	values_agg: 'sum' | 'count' | 'avg' | 'min' | 'max'
}
type PivotWider = { type: 'pivot_wider' } & PivotWiderArgs

type PipelineStep = Source | Filter | Join | Mutate | Summarize | OrderBy | Limit | PivotWider
