import frappe
from frappe import _lt

# The wording the workbook's own title inputs use for an empty title
UNTITLED = {
    "Insights Query v3": _lt("Untitled Query"),
    "Insights Chart v3": _lt("Untitled Chart"),
    "Insights Dashboard v3": _lt("Untitled Dashboard"),
}


@frappe.whitelist()
def search_workbook_items(
    doctype: str,
    txt: str,
    searchfield: str | None = None,
    start: int = 0,
    page_len: int = 20,
    filters: dict | list | None = None,
):
    """Link search for a query, chart or dashboard: its title, then its workbook's title.

    Titles repeat across workbooks, so the workbook is what tells two options apart.
    """
    if doctype not in UNTITLED:
        frappe.throw(frappe._("Cannot search {0}").format(doctype))

    items = frappe.get_list(
        doctype,
        filters=filters,
        or_filters={"title": ["like", f"%{txt}%"], "name": ["like", f"%{txt}%"]},
        fields=["name", "title", "workbook"],
        order_by="modified desc",
        start=start,
        page_length=page_len,
    )
    workbook_titles = dict(
        frappe.get_all(
            "Insights Workbook",
            filters={"name": ["in", list({item.workbook for item in items})]},
            fields=["name", "title"],
            as_list=True,
        )
    )
    return [
        (item.name, item.title or str(UNTITLED[doctype]), workbook_titles.get(item.workbook))
        for item in items
    ]
