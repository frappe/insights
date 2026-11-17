# Frappe has these only on develop (frappe/frappe#46061). On Frappe v15 and v16
# there are no web tier settings, and every caller already falls back to its
# own defaults when there are none.
try:
    from frappe.concurrency_limiter import WebTierSettings, web_tier_settings
except ImportError:
    from typing import NamedTuple

    class WebTierSettings(NamedTuple):
        workers: int
        threads: int
        timeout: int
        graceful_timeout: int

    def web_tier_settings() -> WebTierSettings | None:
        return None


__all__ = ["WebTierSettings", "web_tier_settings"]
