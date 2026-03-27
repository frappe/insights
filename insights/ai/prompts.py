from typing import Any


def get_available_functions() -> list[str]:
    """Return all function names available in expressions."""
    from insights.insights.doctype.insights_data_source_v3.ibis.utils import get_functions

    return sorted(k for k in get_functions() if not k.startswith("_"))


def get_function_signature(func_name: str) -> dict | None:
    """
    Return name, signature, and description for a single function.

    Parses the structured docstring format used in functions.py:
        def func_name(args...)

        Description text.

        Examples:
        - example1
    """
    from insights.insights.doctype.insights_data_source_v3.ibis.utils import get_functions

    func = get_functions().get(func_name)
    if func is None:
        return None

    doc = (getattr(func, "__doc__", "") or "").strip()
    if not doc:
        return {"name": func_name, "signature": func_name + "(...)", "description": "", "examples": []}

    lines = doc.splitlines()
    signature = func_name + "(...)"
    description_lines = []
    examples = []
    in_examples = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("def "):
            signature = stripped[4:]  # strip "def "
        elif stripped.lower().startswith("examples:") or stripped.lower() == "examples":
            in_examples = True
        elif in_examples:
            if stripped.startswith("- "):
                examples.append(stripped[2:])
        else:
            if stripped:
                description_lines.append(stripped)

    return {
        "name": func_name,
        "signature": signature,
        "description": " ".join(description_lines),
        "examples": examples,
    }


def build_expression_guide() -> str:
    """
    Build the full expression language guide with live function reference
    injected from the actual functions registry.
    """
    try:
        functions = get_available_functions()
        func_list = ", ".join(functions)

        # Build compact per-function reference (signature + one-line description)
        sig_lines = []
        for name in functions:
            info = get_function_signature(name)
            if not info:
                continue
            desc = info["description"].split(".")[0] if info["description"] else ""
            example = info["examples"][0] if info["examples"] else ""
            line = f"  - `{info['signature']}`"
            if desc:
                line += f" — {desc}"
            if example:
                line += f". E.g. `{example}`"
            sig_lines.append(line)

        function_reference = "\n".join(sig_lines)
    except Exception:
        func_list = "(unavailable)"
        function_reference = "(unavailable)"

    return f"""\
## Expression Language

The "expression" field uses Python-style syntax with Ibis column semantics. NOT SQL.

Rules:
1. Reference columns by name as Python variables: `revenue`, `order_date`, or `q["%_increment"]` for special characters.
2. Python arithmetic: `+`, `-`, `*`, `/`, `%`
3. Python comparison: `==`, `!=`, `>`, `<`, `>=`, `<=`
4. Boolean: `&` / `|` (not `AND` / `OR`)
5. Always wrap in `{{"type": "expression", "expression": "..."}}`

Correct:
- `revenue - cost`
- `if_else(status == "Returned", 0, amount)`
- `within(order_date, "Last 30 days")`
- `(quantity * unit_price) - discount`
- `coalesce(city, "Unknown")`

Incorrect (do NOT use):
- `SELECT revenue - cost FROM table`
- `CASE WHEN status = 'Returned' THEN 0 ELSE amount END`
- `ifelse(...)` — use `if_else(...)`

## Available Functions

All supported functions (call these by name in expressions):
{func_list}

### Function Reference
{function_reference}\
"""


ROLE = (
    "You are an expert data analyst helping users build & modify queries for a business intelligence tool. "
    'Convert natural language questions into a sequence of "operations" that resembles a query execution plan.'
)

OUTPUT_FORMAT = (
    'Return a single JSON object with one key: "operations" — a JSON array of operation objects. '
    "Return ONLY the JSON object, no markdown fences, no explanation, nothing else."
)

OPERATION_OVERVIEW = """\
## Available Operations

The query is built as a sequence of operations executed in order.
Always start with a \"source\" operation.\
"""

SOURCE_RULES = """\
### Source Operation
Select the table to query from:
```json
{"type": "source", "table": {"type": "table", "data_source": "<data_source>", "table_name": "<table_name>"}}
```
Use the exact data_source value provided in the schema context. Always the first operation.\
"""

FILTER_RULES = """\
### Filter Operation
Filter rows based on conditions.
```json
{
  "type": "filter_group",
  "logical_operator": "And",
  "filters": [
    {"column": {"type": "column", "column_name": "col"}, "operator": "=", "value": "val"},
    {"column": {"type": "column", "column_name": "amount"}, "operator": ">", "value": 100}
  ]
}
```
Use \"Or\" as logical_operator for OR logic.
Supported operators: \"=\", \"!=\", \">\", \">=\", \"<\", \"<=\", \"in\", \"not_in\", \"between\", \"within\",
\"contains\", \"not_contains\", \"starts_with\", \"ends_with\", \"is_set\", \"is_not_set\"
For relative date filters use the \"within\" operator (e.g. value: \"Last 30 days\" or \"Next 7 days\" or \"Current Month\").\
"""

SUMMARIZE_RULES = """\
### Summarize Operation
Aggregate data (GROUP BY equivalent):
```json
{
  "type": "summarize",
  "measures": [
    {"measure_name": "total_sales", "column_name": "sales_amount", "data_type": "Decimal", "aggregation": "sum"}
  ],
  "dimensions": [
    {"dimension_name": "region", "column_name": "region", "data_type": "String"}
  ]
}
```
Supported aggregations: \"sum\", \"count\", \"avg\", \"min\", \"max\", \"count_distinct\"
Measure data_types: \"String\", \"Integer\", \"Decimal\"
Dimension data_types: \"String\", \"Date\", \"Datetime\", \"Time\"\
"""

MUTATE_RULES = """\
### Mutate Operation
Create a calculated column using an expression:
```json
{"type": "mutate", "new_name": "profit", "data_type": "Decimal", "expression": {"type": "expression", "expression": "revenue - cost"}}
```
Supported data_types: \"String\", \"Integer\", \"Decimal\", \"Date\", \"Datetime\", \"Time\", \"Text\"\
"""

ORDER_LIMIT_RULES = """\
### Order By Operation
```json
{"type": "order_by", "column": {"type": "column", "column_name": "col"}, "direction": "asc"}
```
direction: \"asc\" or \"desc\"

### Limit Operation
```json
{"type": "limit", "limit": 100}
```\
"""

SELECT_RENAME_REMOVE_CAST_RULES = """\
### Select Operation
```json
{"type": "select", "column_names": ["col1", "col2"]}
```

### Rename Operation
```json
{"type": "rename", "column": {"type": "column", "column_name": "old_name"}, "new_name": "new_name"}
```

### Remove Operation
```json
{"type": "remove", "column_names": ["col_to_drop"]}
```

### Cast Operation
```json
{"type": "cast", "column": {"type": "column", "column_name": "col"}, "data_type": "Integer"}
```\
"""

JOIN_RULES = """\
### Join Operation
Join another table. join_condition uses either left_column/right_column or a join_expression:
```json
{
  "type": "join",
  "join_type": "inner",
  "table": {"type": "table", "data_source": "<data_source>", "table_name": "<table_name>"},
  "join_condition": {"left_column": {"type": "column", "column_name": "id"}, "right_column": {"type": "column", "column_name": "order_id"}},
  "select_columns": [{"type": "column", "column_name": "col_from_joined_table"}]
}
```
```json
{
  "type": "join",
  "join_type": "inner",
  "table": {"type": "table", "data_source": "<data_source>", "table_name": "<table_name>"},
  "join_condition": {"type": "expression", "expression": "(t1.id == t2.order_id) & (t2.status == 'Active')"},
  "select_columns": [{"type": "column", "column_name": "col_from_joined_table"}]
}
```
join_type: \"inner\", \"left\", \"right\", \"full\"
select_columns: columns to pull in from the joined table.\
"""

UNION_RULES = """\
### Union Operation
Stack rows from another table with the same schema:
```json
{"type": "union", "table": {"type": "table", "data_source": "<data_source>", "table_name": "<table_name>"}, "distinct": true}
```\
"""

PIVOT_RULES = """\
### Pivot Wider Operation
Pivot data from long to wide format:
```json
{
  "type": "pivot_wider",
  "rows": [{"dimension_name": "region", "column_name": "region", "data_type": "String"}],
  "columns": [{"dimension_name": "quarter", "column_name": "quarter", "data_type": "String"}],
  "values": [{"measure_name": "revenue", "column_name": "revenue", "data_type": "Decimal", "aggregation": "sum"}],
  "max_column_values": 50
}
```\
"""


MODIFICATION_RULES = """\
## Handling Follow-up Questions and Modifications

When the user asks to modify an existing query:
1. Start from the CURRENT operations provided
2. Apply ONLY the changes requested
3. Return the COMPLETE updated operations array
4. Keep \"source\" as the first operation with the same table

Common patterns:
- \"add a filter\" → add a filter_group or extend existing one
- \"change grouping\" → update the summarize operation
- \"sort by\" → update or add order_by
- \"show top N\" → add or update limit
- \"instead of X, use Y\" → replace specific columns or conditions\
"""

GENERAL_RULES = """\
## Rules

1. Always start with a \"source\" operation
2. Operations execute in order: filter before summarize, then order/limit
3. Use summarize for any aggregation
4. Column names must match exactly as shown in the schema
5. Use the exact data_source value from the schema context
6. Expressions must be Python-style (Ibis), never SQL\
"""


def build_prompt(parts: list[str]) -> str:
    """Join prompt fragments with double newlines, stripping blanks."""
    return "\n\n".join(p.strip() for p in parts if p and p.strip())


def format_schema(schema: dict[str, Any]) -> str:
    """Render schema dict as a human-readable markdown section."""
    lines = ["## Available Schema"]
    for table_name, table_info in schema.items():
        label = table_info.get("label", table_name)
        lines.append(f"\n### Table: {label} (actual name: {table_name})")
        lines.append("Columns:")
        for col in table_info.get("columns", []):
            col_name = col.get("column", col.get("column_name", ""))
            col_type = col.get("type", "Auto")
            lines.append(f"  - {col_name}: {col_type}")
    return "\n".join(lines)


def build_messages(
    question: str,
    data_source: str,
    schema: dict[str, Any],
    previous_operations: list | None = None,
    conversation: list | None = None,
) -> list[dict]:
    """
    Build the messages list for the initial call.

    Returns a list of dicts with 'role' and 'content' keys suitable
    for passing directly to AIClient.complete().
    """
    import frappe

    system_content = build_prompt(
        [
            ROLE,
            OUTPUT_FORMAT,
            OPERATION_OVERVIEW,
            SOURCE_RULES,
            FILTER_RULES,
            SUMMARIZE_RULES,
            MUTATE_RULES,
            ORDER_LIMIT_RULES,
            SELECT_RENAME_REMOVE_CAST_RULES,
            JOIN_RULES,
            UNION_RULES,
            PIVOT_RULES,
            build_expression_guide(),
            GENERAL_RULES,
            MODIFICATION_RULES,
        ]
    )

    schema_text = format_schema(schema)
    data_source_line = f'Use this exact data_source value in the "source" operation: "{data_source}"'

    user_parts = [
        f"## Question\n\n{question}",
        f"## Data Source\n\n{data_source_line}",
        schema_text,
    ]

    if previous_operations:
        user_parts.insert(
            1,
            f"## Current Query Operations\n\nApply your changes to this existing query:\n```json\n{frappe.as_json(previous_operations)}\n```",
        )

    if conversation:
        history_lines = []
        for msg in conversation:
            role = "User" if msg["role"] == "user" else "Assistant"
            history_lines.append(f"**{role}**: {msg['content']}")
        user_parts.append("## Conversation History\n\n" + "\n".join(history_lines))

    user_parts.append("Generate the query operations JSON object now.")

    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": "\n\n".join(user_parts)},
    ]
    return messages


def append_error_message(
    messages: list[dict],
    error_message: str,
    failed_at_index: int,
    operation_type: str,
    available_columns: list[str],
    partial_sql: str | None,
    attempt: int,
    max_attempts: int,
) -> list[dict]:
    """
    Append an assistant placeholder + a user correction request to messages.
    Returns a new list (does not mutate the original).
    """

    columns_info = (
        "\n".join(f"  - {col}" for col in available_columns)
        if available_columns
        else "No columns available yet (operation failed at source)."
    )

    partial_sql_section = ""
    if partial_sql:
        partial_sql_section = f"\nPartial SQL built so far:\n```sql\n{partial_sql}\n```"

    correction_content = (
        f"## Error (Attempt {attempt} of {max_attempts})\n\n"
        f"The query failed at operation index {failed_at_index} ({operation_type}):\n\n"
        f"Error: {error_message}"
        f"{partial_sql_section}\n\n"
        f"## Columns available after operation {failed_at_index - 1}:\n\n"
        f"{columns_info}\n\n"
        f"Fix the operations and return the COMPLETE corrected JSON object. "
        f"Use only the columns listed above. "
    )

    return [
        *messages,
        {"role": "assistant", "content": "(invalid response — see correction below)"},
        {"role": "user", "content": correction_content},
    ]
