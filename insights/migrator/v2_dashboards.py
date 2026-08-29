"""Translate a v2 dashboard into v3 dashboard items.

A v2 dashboard item carries its own chart, so a chart item becomes two things:
a v3 chart, translated by `chart_translator`, and an item that points at it. The
caller names the v3 charts and queries, and passes those names back in through
`chart_names` and `query_names`.

Everything here is pure: dicts in, dicts out, no database.
"""

from dataclasses import dataclass, field

from insights.migrator.v2_charts import (
    V2_ROW_HEIGHT,
    V3_ROW_HEIGHT,
    Gap,
    TranslatedChart,
    chart_from_dashboard_item,
    parse_json,
    translate_chart,
)

TEXT_ITEM = "Text"
FILTER_ITEM = "Filter"

# insights/query/components/filter_utils.ts - getFilterType()
NUMBER_TYPES = ("Integer", "Decimal")
DATE_TYPES = ("Date", "Datetime", "Time")

# insights/query/components/filter_utils.ts - getOperatorOptions()
OPERATORS_BY_FILTER_TYPE = {
    "String": (
        "in",
        "not_in",
        "contains",
        "not_contains",
        "starts_with",
        "ends_with",
        "is_set",
        "is_not_set",
    ),
    "Number": ("=", "!=", ">", ">=", "<", "<=", "between", "is_set", "is_not_set"),
    "Date": ("between", "=", "!=", ">", ">=", "<", "<=", "within", "is_set", "is_not_set"),
}

# v2 named two operators differently
V2_OPERATOR_ALIASES = {
    "is": "in",
    "timespan": "within",
}

MULTI_VALUE_OPERATORS = ("in", "not_in", "between")


@dataclass
class TranslatedDashboard:
    source: str
    title: str
    items: list[dict] = field(default_factory=list)
    charts: list[TranslatedChart] = field(default_factory=list)
    gaps: list[Gap] = field(default_factory=list)


def translate_layout(layout, item_id: str) -> dict:
    """Carry a v2 layout onto the v3 grid.

    Both grids are 20 columns wide, so x and w travel unchanged. A v2 row is
    30px against v3's 52px, so y and h shrink by that ratio to keep the item
    the same height on screen.
    """
    layout = parse_json(layout)
    scale = V2_ROW_HEIGHT / V3_ROW_HEIGHT
    height = _number(layout.get("h"), 4)
    return {
        "i": str(item_id),
        "x": _number(layout.get("x"), 0),
        "y": max(0, round(_number(layout.get("y"), 0) * scale)),
        "w": _number(layout.get("w"), 10),
        "h": max(1, round(height * scale)),
    }


def _number(value, default):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def filter_type_of(v2_type: str | None) -> str:
    """v2 filters on the column's own type, v3 on one of three filter types."""
    if v2_type in NUMBER_TYPES:
        return "Number"
    if v2_type in DATE_TYPES:
        return "Date"
    return "String"


def translate_dashboard(
    dashboard: dict,
    items: list[dict],
    chart_names: dict[str, str] | None = None,
    query_names: dict[str, str] | None = None,
    columns_by_query: dict[str, list[dict]] | None = None,
    skip_items: list[str] | None = None,
) -> TranslatedDashboard:
    """Convert a v2 dashboard and its items into v3 items.

    `chart_names` maps a v2 dashboard item name to the v3 chart created for it,
    `query_names` maps a v2 query name to its v3 query, and `columns_by_query`
    gives the result columns of each v3 query. All three default to what the v2
    row already holds.

    `skip_items` names the items the caller has already decided cannot be
    carried - an item whose v2 query no longer exists is the case that raises
    it. Emitting one would put a chart with no query on the dashboard and count
    it as converted, so the item is left out here rather than reported twice.
    """
    chart_names = chart_names or {}
    query_names = query_names or {}
    columns_by_query = columns_by_query or {}
    skipped = set(skip_items or ())

    translated = TranslatedDashboard(
        source=dashboard.get("name") or "",
        title=dashboard.get("title") or dashboard.get("name") or "",
    )

    charts_by_key = _index_chart_items(items)
    used_filter_names = set()

    for item in items:
        item_type = item.get("item_type")
        item_id = item.get("item_id") or item.get("name")

        if str(item.get("name") or item_id or "") in skipped:
            continue

        if item_type == TEXT_ITEM:
            translated.items.append(_text_item(item, item_id))
            continue

        if item_type == FILTER_ITEM:
            translated.items.append(
                _filter_item(
                    item,
                    item_id,
                    translated,
                    charts_by_key,
                    chart_names,
                    query_names,
                    columns_by_query,
                )
            )
            continue

        chart = chart_from_dashboard_item(item)
        columns = columns_by_query.get(chart["query"]) if chart["query"] else None
        chart_translation = translate_chart(chart, columns)
        translated.charts.append(chart_translation)
        translated.gaps.extend(chart_translation.gaps)

        if not chart_translation.chart_type:
            continue

        translated.items.append(
            {
                "type": "chart",
                "chart": chart_names.get(item.get("name"), item.get("name")),
                "layout": translate_layout(item.get("layout"), item_id),
            }
        )

    _dedupe_filter_names(translated, used_filter_names)
    return translated


def _text_item(item, item_id):
    options = parse_json(item.get("options"))
    return {
        "type": "text",
        "text": item.get("markdown") or options.get("markdown") or "",
        "layout": translate_layout(item.get("layout"), item_id),
    }


def _index_chart_items(items):
    """A filter links to a chart by item id, by chart name, or by neither.

    Production has both keys in `filter_links` and in `options.links`, so index
    every handle an item answers to.
    """
    index = {}
    for item in items:
        if item.get("item_type") in (TEXT_ITEM, FILTER_ITEM):
            continue
        for key in (item.get("item_id"), item.get("chart"), item.get("name")):
            if key:
                index[str(key)] = item
    return index


def _filter_item(item, item_id, translated, charts_by_key, chart_names, query_names, columns_by_query):
    options = parse_json(item.get("options"))
    column = parse_json(item.get("filter_column")) or options.get("column") or {}

    filter_name = item.get("filter_label") or options.get("label") or f"Filter {item_id}"
    filter_type = filter_type_of(item.get("filter_type") or column.get("type"))

    links, dangling = _filter_links(
        item, charts_by_key, chart_names, query_names, columns_by_query, filter_type
    )
    if dangling:
        translated.gaps.append(
            Gap(
                "filter_link_dangling",
                item.get("name") or str(item_id),
                f"{len(dangling)} link(s) point at an item this dashboard no longer has",
            )
        )

    filter_item = {
        "type": "filter",
        "filter_name": filter_name,
        "filter_type": filter_type,
        "links": links,
        "layout": translate_layout(item.get("layout"), item_id),
    }

    operator = item.get("filter_operator") or options.get("operator")
    operator = V2_OPERATOR_ALIASES.get(operator, operator)
    value = item.get("filter_value")
    if value is None:
        value = options.get("value")

    if operator and operator not in OPERATORS_BY_FILTER_TYPE[filter_type]:
        translated.gaps.append(
            Gap(
                "filter_operator_unsupported",
                item.get("name") or str(item_id),
                f"v3 has no {operator!r} operator for a {filter_type} filter; the default is dropped",
            )
        )
    elif operator:
        filter_item["default_operator"] = operator
        if value not in (None, ""):
            filter_item["default_value"] = _filter_value(operator, value)

    return filter_item


def _filter_value(operator, value):
    """v2 stores a multi-value default as a comma separated string."""
    if operator in MULTI_VALUE_OPERATORS and isinstance(value, str):
        return [part.strip() for part in value.split(",")]
    return value


def _filter_links(item, charts_by_key, chart_names, query_names, columns_by_query, filter_type):
    """Rewrite v2 links onto v3's `{chart: "`query`.`column`"}`.

    v2 keys a link by the dashboard item it filters and names the source table
    column. v3 keys it by chart and names the column of the chart's query, so
    each link needs the item resolved to a chart and to a query.
    """
    options = parse_json(item.get("options"))
    v2_links = parse_json(item.get("filter_links"), default={}) or options.get("links") or {}

    links = {}
    dangling = []
    for key, link in v2_links.items():
        target = charts_by_key.get(str(key))
        if not target:
            dangling.append(key)
            continue

        target_chart = chart_from_dashboard_item(target)
        query = target_chart["query"]
        if not query:
            dangling.append(key)
            continue

        column_name = _link_column(link, columns_by_query.get(query))
        if not column_name:
            dangling.append(key)
            continue

        chart_name = chart_names.get(target.get("name"), target.get("name"))
        query_name = query_names.get(query, query)
        links[chart_name] = f"`{query_name}`.`{column_name}`"

    return links, dangling


def _link_column(link, columns):
    """A v2 link names the source column, v3 names the query's result column.

    The result label is the better guess - a v2 query renames its columns - so
    prefer it, and fall back to the raw column when the query result says the
    label is not there.
    """
    if isinstance(link, str):
        return link
    if not isinstance(link, dict):
        return None

    label = link.get("label")
    column = link.get("column")
    if not columns:
        return label or column

    names = {str(c.get("name") or c.get("label")) for c in columns}
    for candidate in (label, column):
        if candidate and candidate in names:
            return candidate
    return label or column


def _dedupe_filter_names(translated, used):
    """A filter is addressed by its name, so two filters cannot share one."""
    for item in translated.items:
        if item["type"] != "filter":
            continue
        name = item["filter_name"]
        if name not in used:
            used.add(name)
            continue
        suffix = 2
        while f"{name} {suffix}" in used:
            suffix += 1
        item["filter_name"] = f"{name} {suffix}"
        used.add(item["filter_name"])
