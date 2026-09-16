"""Every event Insights sends to Pulse, with the properties `docs/telemetry.md`
puts on all of them."""

import re
from contextlib import suppress

import frappe
from frappe.utils import telemetry as frappe_telemetry
from frappe.utils.caching import site_cache

import insights
from insights.exceptions import (
    ExpressionSyntaxError,
    QueryRefused,
    QueryTimeout,
    UnknownColumn,
)


def default_properties() -> dict:
    return {"app_version": insights.__version__, "entry": get_entry()}


def capture(event: str, interval: str | None = None, **props):
    """Send one event. Telemetry never fails the action it reports on."""
    with suppress(Exception):
        frappe_telemetry.capture(
            event,
            "insights",
            properties={**default_properties(), **props},
            interval=interval,
        )


def capture_share_granted(object: str, with_: str, count: int):
    """`with` is a Python keyword, so the catalogue's property name cannot be a kwarg."""
    capture("share_granted", object=object, count=count, **{"with": with_})


ROW_BUCKETS = ((10_000, "under_10k"), (100_000, "10k_to_100k"), (1_000_000, "100k_to_1m"))
DURATION_BUCKETS = ((1, "under_1s"), (5, "1_to_5s"), (30, "5_to_30s"))


def rows_bucket(n: int) -> str:
    """The bucket `docs/telemetry.md` puts a row count in."""
    return _bucket(n, ROW_BUCKETS, "over_1m")


def duration_bucket(seconds: float) -> str:
    """The bucket `docs/telemetry.md` puts a duration in."""
    return _bucket(seconds, DURATION_BUCKETS, "over_30s")


def _bucket(value, buckets: tuple[tuple[float, str], ...], last: str) -> str:
    """A bucket holds its lower bound and stops short of its upper one."""
    for upper, name in buckets:
        if value < upper:
            return name
    return last


PUNCTUATION = re.compile(r"[^\w\s]")
WHITESPACE = re.compile(r"\s+")


def normalized_publisher(publisher: str) -> str:
    """One spelling for a publisher, so `Pvt. Ltd.` and `Pvt Ltd` are one name."""
    return WHITESPACE.sub(" ", PUNCTUATION.sub(" ", publisher.lower())).strip()


# the three spellings Frappe's own apps declare
STANDARD_PUBLISHERS = frozenset(
    normalized_publisher(name)
    for name in ("Frappe Technologies", "Frappe Technologies Pvt. Ltd.", "Frappe Technologies Pvt Ltd")
)


def is_standard_app(app: str) -> bool:
    """Whether an app's name may leave the site, per `docs/telemetry.md`.

    Frappe publishes it, which the app declares itself in `app_publisher`. The
    name has to be one Frappe's own apps declare: any app on the bench writes
    that hook, so an app called `frappe_crm_addon` passes a substring test.
    """
    try:
        publishers = frappe.get_hooks("app_publisher", app_name=app) or []
    except Exception:
        # reading the hook imports the app, which a faked or broken one cannot satisfy
        return False
    return any(normalized_publisher(publisher) in STANDARD_PUBLISHERS for publisher in publishers)


@site_cache(ttl=24 * 60 * 60)
def get_entry():
    """How the site came to run Insights."""
    if "erpnext" in frappe.get_installed_apps():
        return "erpnext_site"
    if frappe.conf.get("fc_team"):
        return "saas_trial"
    return "self_hosted"


def error_kind(exc: BaseException) -> str:
    """Which kind of failure an exception is, from the closed list in `docs/telemetry.md`.

    The class answers, never the message. Every message here is translated and
    reworded, and a wording change must not move a failure into `other`.
    """
    from ibis.common.exceptions import OperationNotDefinedError

    from insights.insights.doctype.insights_data_source_v3.ibis_utils import (
        CircularQueryReferenceError,
    )
    from insights.insights.doctype.insights_data_source_v3.insights_data_source_v3 import (
        DataSourceConnectionError,
    )

    if isinstance(exc, frappe.PermissionError):
        return "permission"
    if isinstance(exc, QueryTimeout):
        return "timeout"
    if isinstance(exc, DataSourceConnectionError):
        return "connection"
    if isinstance(exc, QueryRefused | CircularQueryReferenceError | OperationNotDefinedError):
        return "refused"
    if isinstance(exc, ExpressionSyntaxError | SyntaxError):
        return "syntax"
    if isinstance(exc, UnknownColumn):
        return "unknown_column"
    return "other"
