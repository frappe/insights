"""
Pydantic models mirroring query.types.ts exactly.

Structure mirrors the TypeScript: shared types first, then Args types, then
the operation = { type } & Args intersection, then the Operation union.

Used in validator.py Pass 1 (structural check) before Ibis semantic validation.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict

_BASE = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Shared types  (mirror: Column, Table, Expression, Measure, Dimension, etc.)
# ---------------------------------------------------------------------------


class Column(BaseModel):
    model_config = _BASE
    type: Literal["column"]
    column_name: str


class TableArgs(BaseModel):
    model_config = _BASE
    type: Literal["table"]
    data_source: str
    table_name: str


class QueryTableArgs(BaseModel):
    model_config = _BASE
    type: Literal["query"]
    query_name: str


Table = TableArgs | QueryTableArgs


class Expression(BaseModel):
    model_config = _BASE
    type: Literal["expression"]
    expression: str


class ColumnMeasure(BaseModel):
    model_config = _BASE
    measure_name: str
    column_name: str
    data_type: Literal["String", "Integer", "Decimal"]
    aggregation: Literal["sum", "count", "avg", "min", "max", "count_distinct"]


class ExpressionMeasure(BaseModel):
    model_config = _BASE
    measure_name: str
    expression: Expression
    data_type: Literal["String", "Integer", "Decimal"]


Measure = ColumnMeasure | ExpressionMeasure


class Dimension(BaseModel):
    model_config = _BASE
    dimension_name: str
    column_name: str
    data_type: Literal["String", "Date", "Datetime", "Time"]
    granularity: str | None = None


ColumnDataType = Literal[
    "String", "Integer", "Decimal", "Date", "Datetime", "Time", "Text", "JSON", "Array", "Auto"
]

FilterOperator = Literal[
    "=",
    "!=",
    ">",
    ">=",
    "<",
    "<=",
    "in",
    "not_in",
    "between",
    "within",
    "contains",
    "not_contains",
    "starts_with",
    "ends_with",
    "is_set",
    "is_not_set",
]

FilterValue = str | int | float | bool | list | None


# FilterArgs = FilterRule | FilterExpression  (neither has a 'type' field in TS)
class FilterRule(BaseModel):
    model_config = _BASE
    column: Column
    operator: FilterOperator
    value: FilterValue | Column = None


class FilterExpression(BaseModel):
    model_config = _BASE
    expression: Expression


Filter = FilterRule | FilterExpression


# JoinCondition — no 'type' field in TS
class JoinConditionColumns(BaseModel):
    model_config = _BASE
    left_column: Column
    right_column: Column


class JoinConditionExpression(BaseModel):
    model_config = _BASE
    join_expression: Expression


JoinCondition = JoinConditionColumns | JoinConditionExpression


# ---------------------------------------------------------------------------
# Operations  (mirror: type + Args intersection pattern)
# ---------------------------------------------------------------------------


class Source(BaseModel):
    model_config = _BASE
    type: Literal["source"]
    table: Table


class FilterGroup(BaseModel):
    model_config = _BASE
    type: Literal["filter_group"]
    logical_operator: Literal["And", "Or"]
    filters: list[Filter]


class Select(BaseModel):
    model_config = _BASE
    type: Literal["select"]
    column_names: list[str]


class Rename(BaseModel):
    model_config = _BASE
    type: Literal["rename"]
    column: Column
    new_name: str


class Remove(BaseModel):
    model_config = _BASE
    type: Literal["remove"]
    column_names: list[str]


class Cast(BaseModel):
    model_config = _BASE
    type: Literal["cast"]
    column: Column
    data_type: ColumnDataType


class Join(BaseModel):
    model_config = _BASE
    type: Literal["join"]
    join_type: Literal["inner", "left", "right", "full"]
    table: Table
    join_condition: JoinCondition
    select_columns: list[Column]


class Union_(BaseModel):
    """Union operation (named Union_ to avoid shadowing typing.Union)."""

    model_config = _BASE
    type: Literal["union"]
    table: Table
    distinct: bool


class Mutate(BaseModel):
    model_config = _BASE
    type: Literal["mutate"]
    new_name: str
    data_type: ColumnDataType
    expression: Expression


class Summarize(BaseModel):
    model_config = _BASE
    type: Literal["summarize"]
    measures: list[Measure]
    dimensions: list[Dimension]


class OrderBy(BaseModel):
    model_config = _BASE
    type: Literal["order_by"]
    column: Column
    direction: Literal["asc", "desc"]


class Limit(BaseModel):
    model_config = _BASE
    type: Literal["limit"]
    limit: int


class PivotWider(BaseModel):
    model_config = _BASE
    type: Literal["pivot_wider"]
    rows: list[Dimension]
    columns: list[Dimension]
    values: list[Measure]
    max_column_values: int | None = None


# ---------------------------------------------------------------------------
# Top-level Operation union  (mirrors query.types.ts Operation)
# ---------------------------------------------------------------------------

Operation = (
    Source
    | FilterGroup
    | Select
    | Rename
    | Remove
    | Cast
    | Join
    | Union_
    | Mutate
    | Summarize
    | OrderBy
    | Limit
    | PivotWider
)
