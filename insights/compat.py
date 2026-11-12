# Frappe v16 has these and Frappe v15 does not. Insights v3 runs on both, and CI
# tests only v16, so code that needs one imports it from here.
import frappe
from frappe.utils import cint

try:
    from frappe.exceptions import ServiceUnavailableError
except ImportError:

    class ServiceUnavailableError(Exception):
        http_status_code = 503


try:
    from frappe.utils import get_currency_precision
except ImportError:

    def get_currency_precision() -> int | None:
        # as Frappe v15's own `fmt_money` reads it
        return cint(frappe.db.get_default("currency_precision")) or None


__all__ = ["ServiceUnavailableError", "get_currency_precision"]
