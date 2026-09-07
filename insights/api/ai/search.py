# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Search the site's vocabulary, for an agent that holds a question in business words.

An agent asking "what do we call revenue here" has to read the site to answer. The
endpoints here give it two things a list of names cannot: a snippet, which says why a
document matched without downloading the document, and usage counts, which say which
of the matches the organisation actually trusts.

Every read goes through `frappe.get_list`, so a document the caller may not read is
never counted, never named, and never quoted.
"""

import re

import frappe
from frappe.utils import add_days, now_datetime

from insights.api.dashboards import dashboard_view_counts
from insights.decorators import insights_whitelist
from insights.insights.doctype.insights_table_v3.insights_table_v3 import get_stored_columns

WORKBOOK = "Insights Workbook"
QUERY = "Insights Query v3"
CHART = "Insights Chart v3"
DASHBOARD = "Insights Dashboard v3"

# the fields each doctype is searched in. `title` ranks above the rest: a title is
# what someone chose to call the thing, a body is where the name happens to appear.
SEARCHED_FIELDS = {
    WORKBOOK: ["title"],
    QUERY: ["title", "operations"],
    CHART: ["title", "config"],
    DASHBOARD: ["title", "items"],
}

SNIPPET_LENGTH = 200
VIEW_WINDOW_DAYS = 30


@insights_whitelist()
def search_content(term: str, limit: int = 20) -> list[dict]:
    """Search every workbook, query, chart and dashboard the caller may read.

    Each hit carries a `snippet`: the part of the matching field that matched, with
    the term marked. That is what makes a hit rankable without a second round trip
    for the document itself.

    Each hit also carries `used_by_charts`, `used_by_dashboards` and
    `dashboard_views` - the last 30 days of opens. They measure reach downstream of
    the hit, so a definition that a busy dashboard reads outranks one nobody opens.
    A count only ever covers documents the caller may read.
    """
    term = (term or "").strip()
    if not term:
        return []

    limit = frappe.utils.cint(limit) or 20

    hits = []
    for doctype, fields in SEARCHED_FIELDS.items():
        hits.extend(_search_doctype(doctype, fields, term, limit))

    _add_workbook_titles(hits)
    _add_usage(hits)

    # rank on reach, and let the most recently touched document win a tie
    hits.sort(key=lambda hit: hit._modified, reverse=True)
    hits.sort(key=_rank)
    return [_without_private_keys(hit) for hit in hits[:limit]]


@insights_whitelist()
def search_columns(term: str, data_source: str | None = None, limit: int = 100) -> list[dict]:
    """Search the column names of every table the caller may read.

    The sync records each table's columns, so this is a database query. A table
    synced before that record existed has nothing to search and is left out.

    A short term matches a lot. `limit` caps the answer, exact names first.
    """
    term = (term or "").strip()
    if not term:
        return []

    limit = frappe.utils.cint(limit) or 100

    needle = term.lower()
    matches = []
    for table in get_stored_columns(data_source, contains=needle).values():
        for column in table.columns:
            name = column.get("name") or ""
            if needle not in name.lower():
                continue
            matches.append(
                {
                    "data_source": table.data_source,
                    "table_name": table.table,
                    "label": table.label,
                    "column": name,
                    "type": column.get("type"),
                }
            )

    # an exact name is the one the asker meant; the rest are near misses
    matches.sort(key=lambda match: (match["column"].lower() != needle, match["column"].lower()))
    return matches[:limit]


def _search_doctype(doctype: str, fields: list[str], term: str, limit: int) -> list[frappe._dict]:
    """The documents of one doctype that match, as hits carrying their snippet."""
    pattern = f"%{_escape_wildcards(term)}%"
    has_workbook = doctype != WORKBOOK

    rows = frappe.get_list(
        doctype,
        or_filters={field: ["like", pattern] for field in fields},
        fields=["name", "title", "modified", *(["workbook"] if has_workbook else []), *fields[1:]],
        order_by="modified desc",
        limit=limit,
    )

    hits = []
    for row in rows:
        field, snippet = _match(row, fields, term)
        hits.append(
            frappe._dict(
                doctype=doctype,
                name=row.name,
                title=row.title,
                workbook=row.workbook if has_workbook else row.name,
                workbook_title=None,
                matched_field=field,
                snippet=snippet,
                used_by_charts=0,
                used_by_dashboards=0,
                dashboard_views=0,
                _modified=row.modified,
            )
        )
    return hits


def _match(row: frappe._dict, fields: list[str], term: str) -> tuple[str, str]:
    """The field that matched and a snippet of it, title first."""
    needle = term.lower()
    for field in fields:
        text = _as_text(row.get(field))
        if needle in text.lower():
            return field, _snippet(text, term)

    # the database matched on a collation python does not share (accents, case
    # folding), so name the field that was searched first and quote it plainly
    return fields[0], _snippet(_as_text(row.get(fields[0])), term)


def _as_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return frappe.as_json(value)


def _snippet(text: str, term: str) -> str:
    """About `SNIPPET_LENGTH` characters of `text` around `term`, with it marked."""
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return ""

    start = text.lower().find(term.lower())
    if start == -1:
        window_start = 0
    else:
        window_start = max(0, start - (SNIPPET_LENGTH - len(term)) // 2)

    window_end = min(len(text), window_start + SNIPPET_LENGTH)
    window_start = max(0, window_end - SNIPPET_LENGTH)
    window = text[window_start:window_end]
    window = re.sub(re.escape(term), lambda match: f"**{match.group(0)}**", window, flags=re.IGNORECASE)

    prefix = "..." if window_start else ""
    suffix = "..." if window_end < len(text) else ""
    return f"{prefix}{window}{suffix}"


def _escape_wildcards(term: str) -> str:
    """`%` and `_` are wildcards to LIKE and literals to whoever typed them."""
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _add_workbook_titles(hits: list[frappe._dict]) -> None:
    workbooks = {hit.workbook for hit in hits if hit.workbook}
    if not workbooks:
        return

    titles = {
        workbook.name: workbook.title
        for workbook in frappe.get_list(
            WORKBOOK,
            filters={"name": ["in", list(workbooks)]},
            fields=["name", "title"],
            limit=0,
        )
    }
    for hit in hits:
        hit.workbook_title = titles.get(hit.workbook)


def _add_usage(hits: list[frappe._dict]) -> None:
    """Count what reads each hit, for the whole list at once.

    Reach is counted downstream. A query is read by the charts built on it and by
    the dashboards those charts sit on. A chart is read by its dashboards. A
    dashboard is where reading stops, so its own opens are the whole measure. A
    workbook is a container, so what it holds is what reads it.
    """
    if not hits:
        return

    by_doctype = {doctype: [hit for hit in hits if hit.doctype == doctype] for doctype in SEARCHED_FIELDS}
    workbooks = [hit.name for hit in by_doctype[WORKBOOK]]
    queries = [hit.name for hit in by_doctype[QUERY]]

    charts_of_query, charts_of_workbook = _charts_reading(queries, workbooks)
    chart_names = {chart for charts in charts_of_query.values() for chart in charts}
    chart_names |= {hit.name for hit in by_doctype[CHART]}
    dashboards_of_chart = _dashboards_showing(chart_names)
    dashboards_of_workbook = _dashboards_of_workbooks(workbooks)

    charts = {}
    dashboards = {}
    for hit in hits:
        key = (hit.doctype, hit.name)
        if hit.doctype == QUERY:
            charts[key] = charts_of_query.get(hit.name, set())
            dashboards[key] = _union(dashboards_of_chart, charts[key])
        elif hit.doctype == CHART:
            charts[key] = set()
            dashboards[key] = dashboards_of_chart.get(hit.name, set())
        elif hit.doctype == DASHBOARD:
            charts[key] = set()
            dashboards[key] = set()
        else:
            charts[key] = charts_of_workbook.get(hit.name, set())
            dashboards[key] = dashboards_of_workbook.get(hit.name, set())

    # a dashboard hit is measured by its own opens, so it counts its own views
    viewed = {name for names in dashboards.values() for name in names}
    viewed |= {hit.name for hit in by_doctype[DASHBOARD]}
    views = dashboard_view_counts(
        list(viewed), since=add_days(now_datetime(), -VIEW_WINDOW_DAYS) if viewed else None
    )

    for hit in hits:
        key = (hit.doctype, hit.name)
        hit.used_by_charts = len(charts[key])
        hit.used_by_dashboards = len(dashboards[key])
        counted = dashboards[key] | ({hit.name} if hit.doctype == DASHBOARD else set())
        hit.dashboard_views = sum(views.get(str(name), 0) for name in counted)


def _charts_reading(queries: list[str], workbooks: list[str]) -> tuple[dict, dict]:
    """The charts that read each query, and the charts each workbook holds."""
    or_filters = {}
    if queries:
        or_filters["query"] = ["in", queries]
        or_filters["data_query"] = ["in", queries]
    if workbooks:
        or_filters["workbook"] = ["in", workbooks]
    if not or_filters:
        return {}, {}

    charts = frappe.get_list(
        CHART,
        or_filters=or_filters,
        fields=["name", "query", "data_query", "workbook"],
        limit=0,
    )

    of_query = {}
    of_workbook = {}
    for chart in charts:
        for query in (chart.query, chart.data_query):
            if query in queries:
                of_query.setdefault(query, set()).add(chart.name)
        if chart.workbook in workbooks:
            of_workbook.setdefault(chart.workbook, set()).add(chart.name)
    return of_query, of_workbook


def _dashboards_showing(charts: set[str]) -> dict[str, set[str]]:
    """The dashboards each chart sits on, of those the caller may read.

    `linked_charts` is an edge table, readable by anyone who may read the child
    doctype, so the parents it names are asked for by name before they count.
    """
    if not charts:
        return {}

    links = frappe.get_all(
        "Insights Dashboard Chart v3",
        filters={"chart": ["in", list(charts)], "parenttype": DASHBOARD},
        fields=["parent", "chart"],
    )
    if not links:
        return {}

    permitted = set(
        frappe.get_list(
            DASHBOARD,
            filters={"name": ["in", list({link.parent for link in links})]},
            pluck="name",
            limit=0,
        )
    )

    showing = {}
    for link in links:
        if link.parent in permitted:
            showing.setdefault(link.chart, set()).add(link.parent)
    return showing


def _dashboards_of_workbooks(workbooks: list[str]) -> dict[str, set[str]]:
    if not workbooks:
        return {}

    dashboards = frappe.get_list(
        DASHBOARD,
        filters={"workbook": ["in", workbooks]},
        fields=["name", "workbook"],
        limit=0,
    )
    of_workbook = {}
    for dashboard in dashboards:
        of_workbook.setdefault(dashboard.workbook, set()).add(dashboard.name)
    return of_workbook


def _union(mapping: dict[str, set[str]], keys: set[str]) -> set[str]:
    found = set()
    for key in keys:
        found |= mapping.get(key, set())
    return found


def _rank(hit: frappe._dict) -> tuple:
    return (
        hit.matched_field != "title",
        -hit.dashboard_views,
        -hit.used_by_dashboards,
        -hit.used_by_charts,
    )


def _without_private_keys(hit: frappe._dict) -> dict:
    return {key: value for key, value in hit.items() if not key.startswith("_")}
