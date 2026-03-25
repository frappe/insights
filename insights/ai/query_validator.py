import traceback
from dataclasses import dataclass, field

import frappe
import ibis

from insights.insights.doctype.insights_data_source_v3.ibis_utils import (
    IbisQueryBuilder,
)
from insights.utils import deep_convert_dict_to_dict as _dict


@dataclass
class ValidationError:
    message: str
    failed_at_index: int
    operation_type: str
    available_columns: list[str] = field(default_factory=list)
    partial_sql: str | None = None


class ValidationQuery:
    def __init__(self, operations: list):
        self.title = "AI Query Validation"
        self.name = "validation_query"
        self.use_live_connection = True
        self.operations = frappe.parse_json(operations) if isinstance(operations, str) else operations


def validate_operations(data_source: str, operations: list) -> tuple[bool, ValidationError | None]:
    print(f"\n--- VALIDATING {len(operations)} OPERATIONS ---")
    doc = ValidationQuery(operations)
    builder = IbisQueryBuilder(doc)
    builder.use_live_connection = True
    builder.query = None
    available_columns: list[str] = []
    partial_sql: str | None = None

    for idx, operation in enumerate(operations):
        print(f"  Building operation [{idx}]: {operation.get('type')}")
        op = _dict(operation)
        try:
            builder.query = builder.perform_operation(op)
            if builder.query is not None:
                available_columns = list(builder.query.columns)
                partial_sql = ibis.to_sql(builder.query)
            print(
                f"  [{idx}] SUCCESS - columns: {available_columns[:5]}{'...' if len(available_columns) > 5 else ''}"
            )
        except BaseException as e:
            tb_str = traceback.format_exception(type(e), e, e.__traceback__)
            error_msg = _extract_error_message(e, tb_str)
            print(f"  [{idx}] FAILED: {error_msg}")

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

    print(f"--- VALIDATION COMPLETE: SUCCESS ---")
    return (True, None)


def _extract_error_message(error: Exception, tb_list: list[str]) -> str:
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
            return line.strip()

    return f"{error_type}: {error_args}" if error_args else error_type
