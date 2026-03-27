import traceback
from dataclasses import dataclass, field

import frappe
import ibis
from pydantic import TypeAdapter
from pydantic import ValidationError as PydanticValidationError

from insights.ai.debug import log
from insights.ai.schemas import Operation
from insights.insights.doctype.insights_data_source_v3.ibis_utils import (
    IbisQueryBuilder,
)
from insights.utils import deep_convert_dict_to_dict as _dict

_operation_adapter = TypeAdapter(Operation)

# Maps the 'type' string in each operation dict to the Pydantic model class name,
# used to filter union validation errors down to the one relevant branch.
_TYPE_TO_MODEL: dict[str, str] = {
    "source": "Source",
    "filter_group": "FilterGroup",
    "select": "Select",
    "rename": "Rename",
    "remove": "Remove",
    "cast": "Cast",
    "join": "Join",
    "union": "Union_",
    "mutate": "Mutate",
    "summarize": "Summarize",
    "order_by": "OrderBy",
    "limit": "Limit",
    "pivot_wider": "PivotWider",
    "window_operation": "WindowOperation",
}


@dataclass
class ValidationError:
    message: str
    failed_at_index: int
    operation_type: str
    available_columns: list[str] = field(default_factory=list)
    partial_sql: str | None = None


class _ValidationQuery:
    """Minimal query-like object accepted by IbisQueryBuilder."""

    def __init__(self, operations: list):
        self.title = "AI Query Validation"
        self.name = "validation_query"
        self.use_live_connection = True
        self.operations = frappe.parse_json(operations) if isinstance(operations, str) else operations


def validate_operations(data_source: str, operations: list[dict]) -> tuple[bool, ValidationError | None]:
    """
    Validate operations in two passes:

    1. Structural (Pydantic) — wrong types, missing fields, bad enum values.
       Fast, no DB needed, produces clear field-level error messages.

    2. Semantic (Ibis) — column references, type mismatches, expression errors.
       Dry-runs through IbisQueryBuilder one operation at a time.

    Returns:
        (True, None) on success.
        (False, ValidationError) on the first failing operation.
    """
    log("validator", "structural validation: {} operations", len(operations))
    # --- Pass 1: structural validation ---
    for idx, operation in enumerate(operations):
        log("validator", "  structure [{}] type={}", idx, operation.get("type", "?"))
        error = _check_structure(idx, operation)
        if error:
            log("validator", "  STRUCTURAL ERROR at [{}]: {}", idx, error.message)
            frappe.logger().debug(
                f"validate_operations: structural error at [{idx}] "
                f"({operation.get('type', '?')}): {error.message}"
            )
            return (False, error)

    log("validator", "structural OK — running semantic validation")
    # --- Pass 2: semantic validation ---
    return _check_semantics(data_source, operations)


def _check_structure(idx: int, operation: dict) -> ValidationError | None:
    """Return a ValidationError if the operation fails Pydantic validation, else None."""
    op_type = operation.get("type", "unknown")
    try:
        _operation_adapter.validate_python(operation)
        return None
    except PydanticValidationError as e:
        message = _format_pydantic_error(e, op_type)
        return ValidationError(
            message=message,
            failed_at_index=idx,
            operation_type=op_type,
        )


def _format_pydantic_error(error: PydanticValidationError, op_type: str) -> str:
    """Format Pydantic validation errors as a compact human-readable string."""
    target_model = _TYPE_TO_MODEL.get(op_type)
    relevant = []

    for err in error.errors():
        loc = err["loc"]
        if not loc:
            continue
        # For top-level Operation union, loc[0] is the model class name tried.
        # Keep only errors from the branch matching this operation's type.
        if isinstance(loc[0], str) and loc[0] in _TYPE_TO_MODEL.values():
            if loc[0] != target_model:
                continue
            field_path = " -> ".join(str(l) for l in loc[1:]) or "(root)"
        else:
            field_path = " -> ".join(str(l) for l in loc)

        relevant.append(f"{field_path}: {err['msg']}")

    if not relevant:
        if target_model is None:
            return f"Unknown operation type: '{op_type}'"
        return str(error)

    prefix = f"Invalid '{op_type}' operation"
    return f"{prefix} — " + "; ".join(relevant)


def _check_semantics(data_source: str, operations: list[dict]) -> tuple[bool, ValidationError | None]:
    """Dry-run operations through IbisQueryBuilder one at a time."""
    doc = _ValidationQuery(operations)
    builder = IbisQueryBuilder(doc)
    builder.use_live_connection = True
    builder.query = None

    available_columns: list[str] = []
    partial_sql: str | None = None

    for idx, operation in enumerate(operations):
        op = _dict(operation)
        log("validator", "  semantic [{}] type={}", idx, op.get("type", "?"))
        try:
            builder.query = builder.perform_operation(op)
            if builder.query is not None:
                available_columns = list(builder.query.columns)
                partial_sql = ibis.to_sql(builder.query)
                log("validator", "  [{}] OK — columns: {}", idx, available_columns)
        except BaseException as e:
            tb_list = traceback.format_exception(type(e), e, e.__traceback__)
            error_msg = _extract_ibis_error(e, tb_list)
            log("validator", "  SEMANTIC ERROR at [{}]: {}", idx, error_msg)
            log("validator", "  traceback:\n{}", "".join(tb_list))
            frappe.logger().debug(
                f"validate_operations: semantic error at [{idx}] " f"({op.get('type', '?')}): {error_msg}"
            )
            return (
                False,
                ValidationError(
                    message=error_msg,
                    failed_at_index=idx,
                    operation_type=op.get("type", "unknown"),
                    available_columns=available_columns,
                    partial_sql=partial_sql,
                ),
            )

    log("validator", "semantic OK")
    return (True, None)


def _extract_ibis_error(error: Exception, tb_list: list[str]) -> str:
    """Normalise Ibis/Python exceptions into compact strings for the retry prompt."""
    error_type = type(error).__name__
    error_args = str(error.args[0]) if error.args else ""

    if error_type == "ValidationError" and error_args:
        return error_args

    if error_type == "AttributeError":
        return error_args if error_args else "Attribute error in operation"

    if error_type == "KeyError":
        return f"Missing key in operation: {error_args}"

    if error_type == "NameError":
        return f"Name error: {error_args}"

    if error_args and len(error_args) < 300:
        return f"{error_type}: {error_args}"

    for line in reversed(tb_list):
        line = line.strip()
        if (
            line.startswith("NameError:")
            or line.startswith("KeyError:")
            or line.startswith("AttributeError:")
        ):
            return line

    return f"{error_type}: {error_args}" if error_args else error_type
