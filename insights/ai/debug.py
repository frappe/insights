"""
Lightweight per-request debug logging for the AI pipeline.

Usage:
    from insights.ai.debug import ailog, get_ai_log, clear_ai_log

    ailog("client", "raw response: {!r}", raw)   # collected when debug=True
    ailog("validator", "structural error at [{}]: {}", idx, msg)

Logs are stored in frappe.local.ai_debug_log (a plain list of strings).
The API endpoint reads this list and attaches it to the response when
the caller passes debug=True.  Nothing is stored between requests.
"""

import frappe


def log(tag: str, msg: str, *args) -> None:
    """
    Append a formatted log line to the per-request debug buffer.

    Always prints to stdout as before (visible in bench logs).
    Only accumulates in frappe.local when the buffer has been initialised
    by the API endpoint (i.e. when debug=True was requested).
    """
    line = f"[AI:{tag}] {msg.format(*args) if args else msg}"
    print(line)

    if hasattr(frappe.local, "ai_debug_log"):
        frappe.local.ai_debug_log.append(line)


def init_ai_log() -> None:
    """Call once at the start of a debug request to enable collection."""
    frappe.local.ai_debug_log = []


def get_ai_log() -> list[str]:
    """Return collected log lines (empty list if debug was not enabled)."""
    return getattr(frappe.local, "ai_debug_log", [])
