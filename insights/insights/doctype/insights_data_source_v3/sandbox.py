"""What code in a query may use.

A script is trusted code, written by an Insights Admin like a Server Script. It
ignores permissions and may make HTTP requests. Anyone who may change a query
may write an expression, so an expression reads only what its Permission User
may read. Neither may write, queue a job, call a method, send mail or register
a commit hook.
"""

import copy

import frappe
import frappe.client
import pandas as pd
from frappe.utils.safe_exec import NamespaceDict, get_python_builtins, get_safe_globals

from insights.permission_user import script_session

from .ibis.utils import BACKEND_ATTRIBUTE_NAMES, is_io_attribute

SCRIPT_NAMES = ("FrappeClient", "json", "orjson", "as_json", "_dict", "dict", "log", "_", "scrub")
SCRIPT_FRAPPE = (
    "get_list",
    "get_all",
    "get_system_settings",
    "get_url",
    "get_fullname",
    "user",
    "lang",
    "format_value",
    "format_date",
    "date_format",
    "time_format",
    "number_format",
    "bold",
    "log",
    "throw",
    "make_get_request",
    "make_post_request",
    "make_put_request",
    "make_patch_request",
    "make_delete_request",
)
SCRIPT_DB = (
    "get_list",
    "get_all",
    "get_value",
    "get_single_value",
    "get_default",
    "exists",
    "count",
    "escape",
    "sql",
)

# frappe's safe data utils, minus those that read a file, fetch a URL, write or
# ignore permissions. Listed by name, so a new frappe release adds none
UTILS = (
    "DATE_FORMAT",
    "TIME_FORMAT",
    "DATETIME_FORMAT",
    "is_invalid_date_string",
    "getdate",
    "get_datetime",
    "to_timedelta",
    "get_timedelta",
    "add_to_date",
    "add_days",
    "add_months",
    "add_years",
    "date_diff",
    "month_diff",
    "time_diff",
    "time_diff_in_seconds",
    "time_diff_in_hours",
    "now_datetime",
    "get_timestamp",
    "get_eta",
    "get_system_timezone",
    "convert_utc_to_system_timezone",
    "now",
    "nowdate",
    "today",
    "nowtime",
    "get_first_day",
    "get_quarter_start",
    "get_quarter_ending",
    "get_first_day_of_week",
    "get_year_start",
    "get_year_ending",
    "get_last_day_of_week",
    "get_last_day",
    "get_time",
    "get_datetime_in_timezone",
    "get_datetime_str",
    "get_date_str",
    "get_time_str",
    "get_user_date_format",
    "get_user_time_format",
    "format_date",
    "format_time",
    "format_datetime",
    "format_duration",
    "get_weekdays",
    "get_weekday",
    "get_timespan_date_range",
    "global_date_format",
    "has_common",
    "flt",
    "cint",
    "floor",
    "ceil",
    "cstr",
    "rounded",
    "remainder",
    "safe_div",
    "round_based_on_smallest_currency_fraction",
    "encode",
    "parse_val",
    "fmt_money",
    "get_number_format_info",
    "money_in_words",
    "in_words",
    "is_html",
    "is_image",
    "strip_html",
    "escape_html",
    "pretty_date",
    "comma_or",
    "comma_and",
    "comma_sep",
    "new_line_sep",
    "filter_strip_join",
    "get_url",
    "get_host_name_from_request",
    "url_contains_port",
    "get_host_name",
    "get_link_to_form",
    "get_link_to_report",
    "get_absolute_url",
    "get_url_to_form",
    "get_url_to_list",
    "get_url_to_report",
    "get_url_to_report_with_filters",
    "compare",
    "make_filter_tuple",
    "make_filter_dict",
    "sanitize_column",
    "scrub_urls",
    "expand_relative_urls",
    "quoted",
    "quote_urls",
    "unique",
    "strip",
    "to_markdown",
    "md_to_html",
    "markdown",
    "is_subset",
    "generate_hash",
    "formatdate",
    "get_abbr",
    "get_month",
    "sha256_hash",
    "parse_json",
    "orjson_dumps",
)

EXPRESSION_NAMES = ("json", "_")
EXPRESSION_FRAPPE = (
    "format_date",
    "date_format",
    "time_format",
    "number_format",
    "bold",
)
DOCUMENT_READS = frozenset({"get", "as_dict", "as_json", "get_formatted", "get_title", "is_new"})
SCRIPT_DOCUMENT_READS = DOCUMENT_READS | {"get_password"}
# the `read_`, `to_` and `from_` methods of a data frame, table or array that
# return a value. Every other one takes a file path, as an array's writers do
IN_MEMORY = frozenset(
    {
        "from_dict",
        "from_records",
        "to_dict",
        "to_frame",
        "to_list",
        "to_numpy",
        "to_period",
        "to_records",
        "to_timestamp",
    }
)
ARRAY_WRITERS = frozenset({"tofile", "dump"})
QUERY_READS = frozenset({"build", "execute"})


def script_globals() -> dict:
    offered = get_safe_globals()
    frappe_names, db_names = offered["frappe"], offered["frappe"].db
    return sandbox_globals(
        offered,
        names={
            **{name: offered[name] for name in SCRIPT_NAMES if name in offered},
            "pandas": NamespaceDict(DataFrame=pd.DataFrame, json_normalize=pd.json_normalize),
        },
        frappe_names={
            **{name: frappe_names[name] for name in SCRIPT_FRAPPE if name in frappe_names},
            "get_doc": script_read(frappe.get_doc),
            "get_cached_doc": script_read(frappe.get_cached_doc),
            "get_last_doc": script_read(frappe.get_last_doc),
            # only the user. The rest of `session` belongs to the caller, CSRF token
            # included, and a run as another user is cached for every caller it serves
            "session": frappe._dict(user=frappe.session.user),
        },
        db_names={name: db_names[name] for name in SCRIPT_DB if name in db_names},
    )


def expression_globals() -> dict:
    offered = get_safe_globals()
    return sandbox_globals(
        offered,
        names={name: offered[name] for name in EXPRESSION_NAMES},
        frappe_names={
            **{name: offered["frappe"][name] for name in EXPRESSION_FRAPPE},
            "get_doc": read_doc,
            "get_list": read_list,
        },
        db_names={"get_value": read_value},
    )


def sandbox_globals(offered: dict, names: dict, frappe_names: dict, db_names: dict) -> dict:
    """The globals code runs with: `names`, and `frappe` holding `frappe_names`, `db_names` and `UTILS`.

    `safe_exec` merges these into frappe's Server Script globals, so every other
    frappe global is replaced with `NotDefined`. The RestrictedPython guards and
    the builtins are kept.
    """
    allowed = {name: value for name, value in offered.items() if name.startswith("_")}
    allowed.update(get_python_builtins())
    allowed.update(names)

    namespace = NamespaceDict(
        frappe_names,
        **{
            name: value
            for name, value in offered["frappe"].items()
            if isinstance(value, type) and issubclass(value, Exception)
        },
    )
    namespace.db = NamespaceDict(db_names)
    utils = offered["frappe"].utils
    namespace.utils = NamespaceDict({name: utils[name] for name in UTILS if name in utils})
    allowed["frappe"] = namespace
    allowed["_getattr_"] = no_io(offered["_getattr_"])

    return {**{name: NotDefined(name) for name in offered}, **allowed}


def no_io(guard):
    """`_getattr_` that refuses file access and the connection a relation runs on."""

    def getattr_(obj, name, default=None):
        owner = obj if isinstance(obj, type) else type(obj)
        if (getattr(owner, "__module__", None) or "").partition(".")[0] in ("pandas", "ibis", "numpy") and (
            name in ARRAY_WRITERS
            or name in BACKEND_ATTRIBUTE_NAMES
            or (is_io_attribute(name) and name not in IN_MEMORY)
        ):
            raise frappe.PermissionError(
                f"Code in a query cannot reach a file or a connection through {name}"
            )
        return guard(obj, name, default)

    return getattr_


class NotDefined:
    def __init__(self, name: str):
        self.name = name

    def __call__(self, *args, **kwargs):
        raise NameError(f"name '{self.name}' is not defined", name=self.name)


def script_read(get):
    def read(*args, **kwargs):
        return DocumentRead(get(*args, **kwargs), SCRIPT_DOCUMENT_READS)

    return read


def read_doc(doctype: str, name=None):
    """Read a document as `frappe.client.get` does, as the Permission User."""
    if not isinstance(doctype, str):
        raise frappe.PermissionError("Code in a query reads a stored document only")

    with script_session():
        doc = frappe.get_doc(doctype, name) if name else frappe.get_doc(doctype)
        doc.check_permission("read")
        doc.apply_fieldlevel_read_permissions()
    return DocumentRead(doc, DOCUMENT_READS)


def read_list(doctype: str, *args, **kwargs):
    with script_session():
        return frappe.client.get_list(doctype, *args, **kwargs)


def read_value(doctype: str, filters=None, fieldname="name", as_dict=False):
    """`frappe.db.get_value`'s arguments, answered by `frappe.client.get_value`."""
    with script_session():
        return frappe.client.get_value(doctype, fieldname, filters, as_dict=as_dict)


class DocumentRead:
    """A document as code in a query sees it: its fields, and only the methods that read it.

    A query's `build` and `execute` read that query, so they check read on it
    for the Permission User.
    """

    __slots__ = ("_doc", "_methods")

    def __init__(self, doc, methods: frozenset[str]):
        self._doc = doc
        self._methods = methods

    def __getattr__(self, name):
        if name in QUERY_READS and self._doc.doctype == "Insights Query v3":
            from insights.permissions import check_referenced_query_access

            check_referenced_query_access(self._doc.name)
            return getattr(self._doc, name)

        value = getattr(self._doc, name)
        if name in self._methods:
            return lambda *args, **kwargs: document_read(value(*args, **kwargs), self._methods)
        if callable(value):
            raise frappe.PermissionError(f"Code in a query cannot call {name} on a document")
        return document_read(value, self._methods)


def document_read(value, methods: frozenset[str]):
    from frappe.model.document import Document

    if isinstance(value, Document):
        return DocumentRead(value, methods)
    if isinstance(value, list | tuple):
        return [document_read(item, methods) for item in value]
    # copied, so code cannot change the document through a dict or set it returns
    if isinstance(value, dict | set):
        return copy.deepcopy(value)
    return value
