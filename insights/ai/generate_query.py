"""
Orchestrates one AI call + retry loop to produce validated query operations.
"""

from typing import Any

import frappe

from insights.ai.client import AIClient
from insights.ai.debug import log
from insights.ai.prompts import append_error_message, build_messages
from insights.ai.validator import validate_operations

MAX_RETRIES = 3

_client = None


def _get_client() -> AIClient:
    global _client
    if _client is None:
        _client = AIClient()
    return _client


def generate_query(
    question: str,
    data_source: str,
    schema: dict[str, Any],
    previous_operations: list | None = None,
    conversation: list | None = None,
) -> dict[str, Any]:
    """
    Generate or modify query operations from a natural language question.

    Args:
        question:            The user's natural language question.
        data_source:         The data source name to query against.
        schema:              Schema dict (table → columns) already restricted to relevant tables.
        previous_operations: Existing operations to modify. None for a fresh query.
        conversation:        Optional conversation history list for follow-up context.

    Returns:
        dict with keys:
            operations: list[dict] | None — generated operations, or None on total failure.
            attempts:   int — how many LLM attempts were made.
            error:      str | None — error message if all retries failed.
    """
    messages = build_messages(
        question=question,
        data_source=data_source,
        schema=schema,
        previous_operations=previous_operations,
        conversation=conversation,
    )
    log("generate_query", "question={!r} data_source={}", question, data_source)
    log("generate_query", "messages built: {}", len(messages))
    for i, m in enumerate(messages):
        log("generate_query", "  [{}] role={} len={}", i, m.get("role", "?"), len(m.get("content", "")))
    return _run_with_retries(messages, data_source)


def _run_with_retries(
    messages: list[dict],
    data_source: str,
    max_retries: int = MAX_RETRIES,
) -> dict[str, Any]:
    client = _get_client()
    operations: list[dict] | None = None
    last_error: dict | None = None

    for attempt in range(1, max_retries + 1):
        log("generate_query", "=== attempt {}/{} ===", attempt, max_retries)
        frappe.logger().debug(f"AI generate_query | attempt {attempt}/{max_retries}")

        try:
            operations = client.complete(messages)
        except ValueError as e:
            log("generate_query", "parse error: {}", e)
            # Bad JSON or missing "operations" key — treat as a retryable error.
            last_error = {
                "message": str(e),
                "failed_at_index": 0,
                "operation_type": "unknown",
                "available_columns": [],
                "partial_sql": None,
            }
            frappe.logger().debug(f"AI generate_query | parse error: {e}")
            if attempt < max_retries:
                messages = append_error_message(
                    messages=messages,
                    error_message=last_error["message"],
                    failed_at_index=0,
                    operation_type="unknown",
                    available_columns=[],
                    partial_sql=None,
                    attempt=attempt,
                    max_attempts=max_retries,
                )
            continue

        log("generate_query", "got {} operations", len(operations))
        import json

        log("generate_query", "operations:\n{}", json.dumps(operations, indent=2))
        frappe.logger().debug(f"Parsed {len(operations)} operations")

        is_valid, validation_error = validate_operations(data_source, operations)

        if is_valid:
            log("generate_query", "validation passed on attempt {}", attempt)
            return {"operations": operations, "attempts": attempt, "error": None}

        last_error = {
            "message": validation_error.message,
            "failed_at_index": validation_error.failed_at_index,
            "operation_type": validation_error.operation_type,
            "available_columns": validation_error.available_columns,
            "partial_sql": validation_error.partial_sql,
        }

        frappe.logger().debug(
            f"Validation failed at index {last_error['failed_at_index']}: {last_error['message']}"
        )
        log(
            "generate_query",
            "validation FAILED at [{}] ({}): {}",
            last_error["failed_at_index"],
            last_error["operation_type"],
            last_error["message"],
        )

        if attempt < max_retries:
            messages = append_error_message(
                messages=messages,
                error_message=last_error["message"],
                failed_at_index=last_error["failed_at_index"],
                operation_type=last_error["operation_type"],
                available_columns=last_error["available_columns"],
                partial_sql=last_error["partial_sql"],
                attempt=attempt,
                max_attempts=max_retries,
            )

    # All retries exhausted — return last attempt result with the error
    return {
        "operations": None,
        "attempts": max_retries,
        "error": last_error["message"] if last_error else "Unknown error after retries",
    }


def _build_schema(data_source: str, table_names: list[str]) -> dict[str, Any]:
    """
    Build a schema dict restricted to the requested tables.
    Keeps the prompt focused and reduces token usage.
    """
    from insights.api.data_sources import get_data_source_table_columns

    schema: dict[str, Any] = {}
    for table_name in table_names:
        try:
            columns = get_data_source_table_columns(data_source, table_name)
        except Exception:
            columns = []

        schema[table_name] = {
            "table": table_name,
            "label": table_name,
            "data_source": data_source,
            "columns": [frappe._dict(column=c.column, label=c.label, type=c.type) for c in columns],
        }

    return schema
