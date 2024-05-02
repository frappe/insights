type Table = {
	type: 'table'
	table_name: string
}
type Column = {
	type: 'column'
	column_name: string
}
type Measure = {
	column_name: string
	data_type: MeasureDataType
	aggregation: AggregationType
}
type Dimension = {
	column_name: string
	data_type: DimensionDataType
	granularity?: GranularityType
}

type ColumnDataType = 'String' | 'Integer' | 'Decimal' | 'Date' | 'Datetime' | 'Time' | 'Text'
type MeasureDataType = 'String' | 'Integer' | 'Decimal'
type DimensionDataType = 'String' | 'Date' | 'Datetime' | 'Time'
type AggregationType = 'sum' | 'count' | 'avg' | 'min' | 'max'
type GranularityType = 'day' | 'week' | 'month' | 'quarter' | 'year'
type DataFormat = 'currency' | 'percent'

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

type FilterArgs =
	| { column: Column; operator: FilterOperator; value: FilterValue | Column }
	| { expression: Expression }
type Filter = { type: 'filter' } & FilterArgs

type SelectArgs = { column_names: string[] }
type Select = { type: 'select' } & SelectArgs

type RenameArgs = { column: Column; new_name: string }
type Rename = { type: 'rename' } & RenameArgs

type RemoveArgs = { column_names: string[] }
type Remove = { type: 'remove' } & RemoveArgs

type CastArgs = { column: Column; data_type: ColumnDataType }
type Cast = { type: 'cast' } & CastArgs

type JoinType = 'inner' | 'left' | 'right' | 'full'
type JoinArgs = { join_type: JoinType; table: Table; left_column: Column; right_column: Column }
type Join = { type: 'join' } & JoinArgs

type Mutation = Expression
type MutateArgs = { new_name: string; data_type: ColumnDataType; mutation: Mutation }
type Mutate = { type: 'mutate' } & MutateArgs

type SummarizeArgs = { measures: Measure[]; dimensions: Dimension[] }
type Summarize = { type: 'summarize' } & SummarizeArgs

type OrderByArgs = { column: Column; direction: 'asc' | 'desc' }
type OrderBy = { type: 'order_by' } & OrderByArgs

type Limit = { type: 'limit'; limit: number }

type WindowOperationType = 'sum' | 'lag_difference' | 'row_number'
type WindowOperationArgs = {
	op: WindowOperationType
	column: Column
	partition_by?: Column
	order_by?: Column
}
type WindowOperation = { type: 'window_operation' } & WindowOperationArgs

type PivotWiderArgs = {
	rows: Dimension[]
	columns: Dimension[]
	values: Measure[]
}
type PivotWider = { type: 'pivot_wider' } & PivotWiderArgs

type Operation =
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
