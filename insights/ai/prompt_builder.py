from typing import Any

import frappe

SYSTEM_PROMPT = """You are an expert data analyst helping users build queries for a business intelligence tool.

Your task is to convert natural language questions into query operations that can be executed against a database.

## Available Operations

The query is built as a sequence of operations:

### 1. Source Operation
Select the table to query from:
```json
{
  "type": "source",
  "table": {
    "type": "table",
    "data_source": "REPLACE_WITH_ACTUAL_DATA_SOURCE_NAME",
    "table_name": "actual_table_name"
  }
}
```
IMPORTANT: Use the exact data_source value provided in the "Data Source" section above.

### 2. Filter Group
Filter rows based on conditions:

```json
{
  "type": "filter_group",
  "logical_operator": "And",
  "filters": [
    {"column": {"type": "column", "column_name": "column_name"}, "operator": "=", "value": "some_value"},
    {"column": {"type": "column", "column_name": "column_name"}, "operator": ">", "value": 100}
  ]
}
```

For OR logic, use "Or" as the logical_operator.

Supported operators: "=", "!=", ">", ">=", "<", "<=", "in", "not_in", "between", "within", "contains", "not_contains", "starts_with", "ends_with", "is_set", "is_not_set"

### 3. Select Operation
Choose specific columns to include:
```json
{
  "type": "select",
  "column_names": ["col1", "col2"]
}
```

### 4. Summarize Operation
Aggregate data (GROUP BY equivalent):
```json
{
  "type": "summarize",
  "measures": [
    {
      "measure_name": "total_sales",
      "column_name": "sales_amount",
      "data_type": "Decimal",
      "aggregation": "sum"
    }
  ],
  "dimensions": [
    {"dimension_name": "region", "column_name": "region", "data_type": "String"}
  ]
}
```

Supported aggregations: "sum", "count", "avg", "min", "max", "count_distinct"
Supported dimension data_types: "String", "Date", "Datetime", "Time"
Supported measure data_types: "String", "Integer", "Decimal"

### 5. Order By Operation
Sort results:
```json
{
  "type": "order_by",
  "column": {"type": "column", "column_name": "column_name"},
  "direction": "asc"
}
```

### 6. Limit Operation
Limit number of results:
```json
{
  "type": "limit",
  "limit": 100
}
```

### 7. Mutate Operation
Create calculated columns:
```json
{
  "type": "mutate",
  "new_name": "profit",
  "data_type": "Decimal",
  "expression": {
    "type": "expression",
    "expression": "revenue - cost"
  }
}
```

## Expression Language (CRITICAL)

The `expression` field uses **Python-style expression syntax with Insights/Ibis columns and functions**.
It is **NOT SQL**.

Use these rules:
1. Treat each column as a Python variable by name (example: `revenue`, `order_date`)
2. Use Python operators (`+`, `-`, `*`, `/`, `%`, `==`, `!=`, `>`, `<`, `>=`, `<=`)
3. Use Python boolean operators `and` / `or` for scalar logic, and `&` / `|` for column conditions
4. Use available helper functions such as `within()`, `date_add()`, `date_sub()`, `ifelse()`, `coalesce()`
5. Return a single valid expression string; no SQL keywords

Correct expression examples:
- `revenue - cost`
- `ifelse(status == "Returned", 0, amount)`
- `within(order_date, "Last 30 days")`
- `(quantity * unit_price) - discount`
- `coalesce(city, "Unknown")`

Incorrect expression examples (DO NOT USE):
- `SELECT revenue - cost FROM table`
- `CASE WHEN status = 'Returned' THEN 0 ELSE amount END`
- `WHERE order_date >= CURRENT_DATE - INTERVAL '30 day'`
- `` `revenue` - `cost` ``

## Important Rules

1. ALWAYS start with a "source" operation
2. ALWAYS use "filter_group" for ALL filters - never use standalone "filter"
3. Operations are executed in order - filter before summarize, then order/limit
4. Use summarize for any aggregation queries
5. Column names must match exactly as shown in the schema
6. Data source must be an existing data source from the provided schema
7. Wrap expressions in {"type": "expression", "expression": "..."} format
8. Expressions must be Python-style (Insights/Ibis), never SQL
9. Return ONLY the JSON array of operations, nothing else
10. For date filters, use "within" operator for relative dates (e.g., "within the last 30 days")
11. Be precise with column references - use the actual column_name from schema

## Handling Follow-up Questions

When the user asks a follow-up question or asks to modify the query:
1. Start from the CURRENT query operations provided
2. Apply ONLY the changes requested by the user
3. Return the COMPLETE updated operations array
4. The first operation should still be "source" - keep the existing data source and table

Common modification patterns:
- "add a filter": Add a new filter_group or extend existing one
- "change grouping": Update the summarize operation
- "sort by": Update or add order_by operation
- "show top 10": Add or update limit operation
- "instead of X, use Y": Replace specific columns or conditions

## Output Format

Return a JSON array of operations that implements the user's request."""


class PromptBuilder:
    def __init__(self, schema: dict[str, Any], question: str, data_source: str):
        self.schema = schema
        self.question = question
        self.data_source = data_source

    def build(
        self,
        previous_operations: list | None = None,
        conversation_history: list | None = None,
    ) -> str:
        schema_description = self._format_schema()

        context_section = ""
        if previous_operations:
            context_section = f"""

## Current Query Operations

The user has an existing query. Apply your changes to this query:
```json
{frappe.as_json(previous_operations)}
```
"""

        history_section = ""
        if conversation_history:
            history_lines = []
            for msg in conversation_history:
                role = "User" if msg["role"] == "user" else "Assistant"
                history_lines.append(f"**{role}**: {msg['content']}")
            history_section = f"""

## Conversation History

{chr(10).join(history_lines)}
"""

        return f"""{SYSTEM_PROMPT}

## User Question

{self.question}
{context_section}{history_section}
## Data Source

Use this exact data_source value in the "source" operation: "{self.data_source}"

## Available Schema

{schema_description}

## Generate Query Operations

Based on the question and schema above, generate the appropriate query operations as a JSON array.
"""

    def _format_schema(self) -> str:
        lines = []
        for table_name, table_info in self.schema.items():
            label = table_info.get("label", table_name)
            lines.append(f"\n### Table: {label} (actual name: {table_name})")
            lines.append("Columns:")
            for col in table_info.get("columns", []):
                col_name = col.get("column", col.get("column_name", ""))
                col_type = col.get("type", "Auto")
                lines.append(f"  - {col_name}: {col_type}")
        return "\n".join(lines)

    def build_correction_prompt(
        self,
        current_operations: list,
        error_message: str,
        failed_at_index: int,
        operation_type: str,
        available_columns: list[str],
        partial_sql: str | None,
        attempt: int,
        max_attempts: int,
    ) -> str:
        schema_description = self._format_schema()

        columns_info = "No columns available yet (operation failed at source)."
        if available_columns:
            columns_info = "\n".join(f"  - {col}" for col in available_columns)

        partial_sql_info = ""
        if partial_sql:
            partial_sql_info = f"\nPartial SQL built so far:\n```sql\n{partial_sql}\n```"

        return f"""{SYSTEM_PROMPT}

## User Question

{self.question}

## Data Source

Use this exact data_source value in the "source" operation: "{self.data_source}"

## Available Schema

{schema_description}

## Error (Attempt {attempt} of {max_attempts})

The query build failed at operation index {failed_at_index} ({operation_type}):

Error: {error_message}
{partial_sql_info}

## Columns Available at Failed Point

The following columns exist after operation {failed_at_index - 1}:

{columns_info}

## Previous Operations

These operations were already validated and are working correctly:

```json
{frappe.as_json(current_operations[:failed_at_index]) if failed_at_index > 0 else "[]"}
```

## Your Task

Fix the operations to address the error:
- Use "filter_group" for ALL filters - never use standalone "filter"
- Use ONLY the columns listed above
- Do NOT reuse column names that were removed by previous operations
- If using mutate/expression, use Python-style Insights/Ibis expressions (not SQL)
- Return the COMPLETE corrected JSON array with all operations
- Return ONLY the JSON array, nothing else
"""
