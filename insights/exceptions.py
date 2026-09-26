"""The exceptions a run raises, and the only thing `error_kind` reads.

A refusal includes a message for the user and a class for the code. The message
is translated and reworded. The class is what `insights.telemetry.error_kind`
maps to the closed list in `docs/telemetry.md`.
"""

import frappe


class QueryRefused(frappe.ValidationError):
    """The engine will not run this query."""


class UnknownColumn(frappe.ValidationError):
    """A column, table or query the pipeline names is not there."""


class QueryTimeout(frappe.ValidationError):
    """The run passed the execution limit."""


class ExpressionSyntaxError(frappe.ValidationError):
    """An expression or a script the engine cannot read."""
