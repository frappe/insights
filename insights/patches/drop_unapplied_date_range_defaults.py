import frappe

from insights.upgrade import add_item

DASHBOARD = "Insights Dashboard v3"


def execute():
    """Remove the date range defaults Insights 3 stored as text and never applied.

    Editors from 3.7 to 3.11 stored a `between` default as `"from,to"`. Insights 3
    showed the range in the filter but applied only a pair of dates, so the
    dashboard opened on every date. Insights 4 applies the default and reads the
    text's first two characters as the range, so the cards open empty or fail.
    Removing it keeps the rows the dashboard showed. Splitting it would apply a
    range nobody saw applied, which is often years old by now. The owner is told
    the range, to set it again.
    """
    for dashboard in frappe.get_all(DASHBOARD, fields=["name", "title", "owner", "items"]):
        items = frappe.parse_json(dashboard["items"])
        if not isinstance(items, list):
            continue

        dropped = drop_unapplied_ranges(items)
        if not dropped:
            continue
        for item in dropped:
            report(dashboard, item)
        frappe.db.set_value(DASHBOARD, dashboard.name, "items", frappe.as_json(items), update_modified=False)


def drop_unapplied_ranges(items: list) -> list[dict]:
    """Remove each unapplied range default from `items`, in place. Answers each
    filter it removed one from, with the range it held."""
    dropped = []
    for item in items:
        if is_unapplied_range(item):
            dropped.append({**item})
            del item["default_value"]
    return dropped


def is_unapplied_range(item) -> bool:
    return (
        isinstance(item, dict)
        and item.get("type") == "filter"
        and item.get("filter_type") == "Date"
        and item.get("default_operator") == "between"
        and isinstance(item.get("default_value"), str)
        and bool(item["default_value"])
    )


def report(dashboard, item) -> None:
    start, _, end = item["default_value"].partition(",")
    add_item(
        "K1",
        f'Dashboard "{dashboard.title or dashboard.name}" showed {start} to {end} as the default of its filter '
        f'"{item.get("filter_name")}", but Insights 3 never applied it, so the dashboard showed every date. '
        "The default is removed to keep it that way. Set it again to apply the range.",
        reference=(DASHBOARD, dashboard.name),
        user=None if dashboard.owner == "Administrator" else dashboard.owner,
    )
