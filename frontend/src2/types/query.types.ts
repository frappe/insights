import { GranularityType } from "../helpers/constants";

export type TableArgs = { type: 'table'; data_source: string; table_name: string }
export type QueryTableArgs = {
	type: 'query'
	workbook: string
	query_name: string
	operations?: Operation[]
}
export type Table = TableArgs | QueryTableArgs
export type Column = {
	type: 'column'
	column_name: string
}
export type Measure = ColumnMeasure | ExpressionMeasure
export type ColumnMeasure = {
	measure_name: string
	column_name: string
	data_type: MeasureDataType
	aggregation: AggregationType
}
export type ExpressionMeasure = {
	measure_name: string
	expression: Expression
	data_type: MeasureDataType
}
export type MeasureOption = Measure & { label: string; value: string }
export type Dimension = {
	dimension_name: string
	column_name: string
	data_type: DimensionDataType
	granularity?: GranularityType
}
export type DimensionOption = Dimension & { label: string; value: string }

export type ColumnDataType =
	| 'String'
	| 'Integer'
	| 'Decimal'
	| 'Date'
	| 'Datetime'
	| 'Time'
	| 'Text'
export type MeasureDataType = 'String' | 'Integer' | 'Decimal'
export type DimensionDataType = 'String' | 'Date' | 'Datetime' | 'Time'
export const aggregations = ['sum', 'count', 'avg', 'min', 'max', 'count_distinct']
export type AggregationType = (typeof aggregations)[number]
export type DataFormat = 'currency' | 'percent'

export type FilterOperator =
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
export type FilterValue = string | number | boolean | any[] | string[] | undefined
export type Expression = {
	type: 'expression'
	expression: string
}

export type SourceArgs = { table: Table }
export type Source = { type: 'source' } & SourceArgs

export type LogicalOperator = 'And' | 'Or'
export type FilterRule = {
	column: Column
	operator: FilterOperator
	value: FilterValue | Column
}
export type FilterExpression = { expression: Expression }
export type FilterArgs = FilterRule | FilterExpression
export type Filter = { type: 'filter' } & FilterArgs

export type FilterGroupArgs = { logical_operator: LogicalOperator; filters: FilterArgs[] }
export type FilterGroup = { type: 'filter_group' } & FilterGroupArgs
export type AdhocFilters = Record<string, FilterGroup>

export type SelectArgs = { column_names: string[] }
export type Select = { type: 'select' } & SelectArgs

export type RenameArgs = { column: Column; new_name: string }
export type Rename = { type: 'rename' } & RenameArgs

export type RemoveArgs = { column_names: string[] }
export type Remove = { type: 'remove' } & RemoveArgs

export type CastArgs = { column: Column; data_type: ColumnDataType }
export type Cast = { type: 'cast' } & CastArgs

export type JoinType = 'inner' | 'left' | 'right' | 'full'
export type JoinCondition =
	| { left_column: Column; right_column: Column }
	| { join_expression: Expression }
export type JoinArgs = {
	join_type: JoinType
	table: Table
	select_columns: Column[]
	join_condition: JoinCondition
}
export type Join = { type: 'join' } & JoinArgs

export type UnionArgs = { table: Table, distinct: boolean }
export type Union = { type: 'union' } & UnionArgs

export type MutateArgs = { new_name: string; data_type: ColumnDataType; expression: Expression }
export type Mutate = { type: 'mutate' } & MutateArgs

export type SummarizeArgs = { measures: Measure[]; dimensions: Dimension[] }
export type Summarize = { type: 'summarize' } & SummarizeArgs

export type OrderByArgs = { column: Column; direction: 'asc' | 'desc' }
export type OrderBy = { type: 'order_by' } & OrderByArgs
export type SortDirection = 'asc' | 'desc' | ''
export type SortOrder = Record<string, SortDirection>

export type Limit = { type: 'limit'; limit: number }

export type WindowOperationType = 'sum' | 'lag_difference' | 'row_number'
export type WindowOperationArgs = {
	op: WindowOperationType
	column: Column
	partition_by?: Column
	order_by?: Column
}
export type WindowOperation = { type: 'window_operation' } & WindowOperationArgs

export type PivotWiderArgs = {
	rows: Dimension[]
	columns: Dimension[]
	values: Measure[]
	max_column_values?: number
}
export type PivotWider = { type: 'pivot_wider' } & PivotWiderArgs

export type CustomOperationArgs = { expression: Expression }
export type CustomOperation = { type: 'custom_operation' } & CustomOperationArgs

export type SQLArgs = { raw_sql: string, data_source: string }
export type SQL = { type: 'sql' } & SQLArgs

export type CodeArgs = { code: string }
export type Code = { type: 'code' } & CodeArgs

export type Operation =
	| Source
	| Filter
	| FilterGroup
	| Select
	| Rename
	| Remove
	| Cast
	| Join
	| Union
	| Mutate
	| Summarize
	| OrderBy
	| Limit
	| PivotWider
	| CustomOperation
	| SQL
	| Code

export type QueryResultRow = Record<string, any>
export type QueryResultColumn = {
	name: string
	type: ColumnDataType
}

export type DropdownOption = {
	label: string
	value: string
	description?: string
}

export type GroupedDropdownOption = {
	group: string
	items: DropdownOption[]
}

export type ColumnOption = DropdownOption & {
	query: string
	data_type: ColumnDataType
}

export type GroupedColumnOption = {
	group: string
	items: ColumnOption[]
}

export type QueryResult = {
	executedSQL: string
	totalRowCount: number
	rows: QueryResultRow[]
	formattedRows: QueryResultRow[]
	columns: QueryResultColumn[]
	columnOptions: ColumnOption[]
	timeTaken: number
	lastExecutedAt: Date
}
