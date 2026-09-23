import frappe

from insights.insights.doctype.insights_dashboard_v3.insights_dashboard_v3 import LINK_COLUMN
from insights.insights.doctype.insights_workbook.insights_workbook import _rewrite_query_references
from insights.insights.query_utils import referenced_queries

QUERY = "Insights Query v3"
DASHBOARD = "Insights Dashboard v3"


def execute():
    """Give every workbook its own copy of the queries it sources from another one.

    A query's sources are queries of its own workbook, and a save or a run of
    one that sources another workbook's is refused. So each such source is
    copied into the reading workbook with every query it reads in turn, once
    per reading workbook, and the reference points at the copy. The originals
    are left as they are.

    A variable is copied by name and not by value. It holds a script's
    credential, and the copy is the reading workbook's to edit. Copying
    without it keeps every reference inside its own workbook, where it runs;
    refusing the copy would leave the reference refused at every run. So the
    copies that need a value entered are named instead.
    """
    workbook_of = dict(frappe.get_all(QUERY, fields=["name", "workbook"], as_list=True))
    # Copied and rewritten from as they were before the patch. A reader the
    # loop has already rewritten names a copy, and copying from it again keys
    # the next copy by that copy instead of by the original a filter links.
    stored = dict(
        frappe.get_all(
            QUERY,
            filters={"operations": ("like", "%query_name%")},
            fields=["name", "operations"],
            as_list=True,
        )
    )

    by_reader = {}
    for reader, workbook, source in foreign_sources(workbook_of):
        by_reader.setdefault((reader, workbook), set()).add(source)

    copies = {}
    for (reader, workbook), sources in by_reader.items():
        id_map = {source: copy_into(source, workbook, copies, workbook_of, stored) for source in sources}
        doc = frappe.get_doc(QUERY, reader)
        doc.operations = _rewrite_query_references(stored[reader], id_map, workbook)
        doc.save(ignore_permissions=True)

    repoint_filter_links(copies)


def repoint_filter_links(copies: dict):
    """Link each dashboard filter that names an original to the copy its card now reads.

    A link is followed only to a query the card reads, and the card's workbook
    reads the copy.
    """
    if not copies:
        return

    workbook_of_chart = dict(frappe.get_all("Insights Chart v3", fields=["name", "workbook"], as_list=True))
    for dashboard in frappe.get_all(DASHBOARD, fields=["name", "items"]):
        items = frappe.parse_json(dashboard["items"]) or []
        repointed = False
        for item in items:
            links = item.get("links") if item.get("type") == "filter" else None
            for chart, link in (links or {}).items():
                match = LINK_COLUMN.match(link or "")
                copy = match and copies.get((match.group(1), workbook_of_chart.get(chart)))
                if copy:
                    links[chart] = f"`{copy}`.`{match.group(2)}`"
                    repointed = True
        if repointed:
            frappe.db.set_value(
                DASHBOARD, dashboard["name"], "items", frappe.as_json(items), update_modified=False
            )


def foreign_sources(workbook_of: dict | None = None) -> list[tuple[str, str, str]]:
    """Every (reading query, its workbook, source query) whose source sits in another workbook.

    A source no row holds is left out: there is nothing to copy.
    """
    if workbook_of is None:
        workbook_of = dict(frappe.get_all(QUERY, fields=["name", "workbook"], as_list=True))

    return [
        (reader.name, reader.workbook, source)
        for reader in frappe.get_all(
            QUERY,
            filters={"operations": ("like", "%query_name%")},
            fields=["name", "workbook", "operations"],
        )
        for source in sorted(referenced_queries(reader.operations))
        if source in workbook_of and workbook_of[source] != reader.workbook
    ]


def copy_into(original: str, workbook: str, copies: dict, workbook_of: dict, stored: dict) -> str:
    """The copy of `original` in `workbook`, made the first time it is asked for.

    `stored` is every query's operations before the patch wrote any, so the
    copy reads the originals `original` read, and each is keyed by itself.
    """
    if (original, workbook) in copies:
        return copies[(original, workbook)]

    source = frappe.get_doc(QUERY, original)
    operations = stored.get(original, source.operations)
    id_map = {
        ref: copy_into(ref, workbook, copies, workbook_of, stored)
        for ref in referenced_queries(operations)
        if ref in workbook_of and workbook_of[ref] != workbook
    }

    copy = frappe.new_doc(QUERY)
    copy.update(
        {
            "title": source.title,
            "workbook": workbook,
            "operations": _rewrite_query_references(operations, id_map, workbook),
            "use_live_connection": source.use_live_connection,
            "is_script_query": source.is_script_query,
            "is_builder_query": source.is_builder_query,
            "is_native_query": source.is_native_query,
        }
    )
    for variable in source.variables:
        copy.append("variables", {"variable_name": variable.variable_name})
    # the value is required, and it is the one thing the copy must not carry
    copy.flags.ignore_mandatory = True
    copy.insert(ignore_permissions=True)
    if source.variables:
        print(
            f"Query {copy.name} in workbook {workbook} is a copy of {original} without its variable"
            f" values: {', '.join(variable.variable_name for variable in source.variables)}"
        )
    copies[(original, workbook)] = copy.name
    workbook_of[copy.name] = workbook
    return copy.name
