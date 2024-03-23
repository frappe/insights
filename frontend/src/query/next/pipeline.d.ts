type Table = {
	type: 'table'
	table_name: string
}
type Column = {
	type: 'column'
	column_name: string
	options?: ColumnOptions
}
type ColumnType = 'String' | 'Integer' | 'Decimal' | 'Date' | 'Datetime' | 'Time' | 'Text'

type ColumnOptions = {
	date_format?: string
	aggregate?: string
}
type FilterOperator =
	| '='
	| '!='
	| '>'
	| '>='
	| '<'
	| '<='
	| 'in'
	| 'not_in'
	| 'between'
	| 'within'
	| 'contains'
	| 'not_contains'
	| 'starts_with'
	| 'ends_with'
	| 'is_set'
	| 'is_not_set'
type FilterValue = string | number | boolean | any[] | string[] | undefined
type Expression = {
	type: 'expression'
	expression: string
}

type SourceArgs = { table: Table }
type Source = { type: 'source' } & SourceArgs

type FilterArgs = { column: Column; operator: FilterOperator; value: FilterValue | Column }
type Filter = { type: 'filter' } & FilterArgs

type SelectArgs = { column_names: string[] }
type Select = { type: 'select' } & SelectArgs

type RenameArgs = { column: Column; new_name: string }
type Rename = { type: 'rename' } & RenameArgs

type RemoveArgs = { column_names: string[] }
type Remove = { type: 'remove' } & RemoveArgs

type CastArgs = { column: Column; data_type: string }
type Cast = { type: 'cast' } & CastArgs

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

type PipelineStep =
	| Source
	| Filter
	| Select
	| Rename
	| Remove
	| Cast
	| Join
	| Mutate
	| Summarize
	| OrderBy
	| Limit
	| PivotWider
