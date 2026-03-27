import frappe

from insights.ai.debug import get_ai_log, init_ai_log
from insights.ai.generate_query import _build_schema
from insights.ai.generate_query import generate_query as _generate_query
from insights.decorators import insights_whitelist


@insights_whitelist()
def generate_query(
    question: str,
    data_source: str,
    table_names: list[str],
    current_operations: list | None = None,
    debug: bool = False,
):
    """
    Stateless endpoint for AI-assisted query building.

    Generate a new query or modify an existing one from a natural language question.
    Schema context is restricted to the provided table_names for focus and efficiency.

    Args:
        question:           Natural language description of the desired query.
        data_source:        Name of the Insights Data Source v3 to query.
        table_names:        Tables to include in schema context (at least one required).
        current_operations: Current query operations to modify. Omit for fresh generation.
        debug:              If True, attach collected log lines as "debug_log" in response.

    Returns:
        {
            "operations": [...] | null,
            "attempts": int,
            "error": str | null,
            "debug_log": [...] | null   # only present when debug=True
        }
    """
    if not question or not question.strip():
        frappe.throw("Question cannot be empty")

    if not data_source:
        frappe.throw("Data source is required")

    if not table_names or not isinstance(table_names, list) or len(table_names) == 0:
        frappe.throw("At least one table must be selected")

    if debug:
        init_ai_log()

    schema = _build_schema(data_source, table_names)

    result = _generate_query(
        question=question.strip(),
        data_source=data_source,
        schema=schema,
        previous_operations=current_operations or None,
    )

    if debug:
        result["debug_log"] = get_ai_log()

    return result
