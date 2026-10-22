import frappe

from insights.insights.doctype.insights_dashboard_v3.insights_dashboard_v3 import LINK_COLUMN
from insights.insights.query_utils import referenced_queries, sync_query_references
from insights.upgrade import add_item
from insights.utils import deep_convert_dict_to_dict

QUERY = "Insights Query v3"
WORKBOOK = "Insights Workbook"
DASHBOARD = "Insights Dashboard v3"


def execute():
    """Give every workbook its own copy of each query it uses from another workbook.

    A query may only use queries of its own workbook as sources, and saving or
    running one that uses another workbook's query is refused. So each such
    source is copied into the workbook that uses it, with every query it reads
    in turn, once per workbook, and the reference is changed to the copy. The
    originals are not changed.

    A variable is copied by name, not by value. Its value may be a script's
    credential, and the copy belongs to another workbook. Copying without the
    value keeps every reference inside its own workbook, where it can run.
    Refusing the copy would leave the reference refused on every run. So each
    copy that needs a value entered is an upgrade item for the workbook's owner.

    A query whose workbook was deleted is left as it is: nobody can open it,
    and a copy cannot be made into a workbook that is not there.
    """
    workbook_of = dict(frappe.get_all(QUERY, fields=["name", "workbook"], as_list=True))
    workbooks = set(frappe.get_all(WORKBOOK, pluck="name"))
    # Copy and rewrite from the operations as they were before the patch. A
    # query the loop has already rewritten names a copy. Copying from it again
    # would key the next copy by that copy, not by the original a filter links.
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
        if workbook not in workbooks:
            continue
        by_reader.setdefault((reader, workbook), set()).add(source)

    copies = {}
    for (reader, workbook), sources in by_reader.items():
        id_map = {source: copy_into(source, workbook, copies, workbook_of, stored) for source in sources}
        operations = rewrite_query_references(stored[reader], id_map, workbook)
        frappe.db.set_value(QUERY, reader, "operations", operations, update_modified=False)
        sync_query_references(reader, operations)

    repoint_filter_links(copies)


def rewrite_query_references(operations, id_map: dict, workbook: str) -> str:
    """Point every source in `operations` that `id_map` names at its copy in `workbook`."""
    operations = deep_convert_dict_to_dict(frappe.parse_json(operations) or [])
    for op in operations:
        table = op.get("table") or {}
        if table.get("type") == "query" and table.get("query_name") in id_map:
            table["query_name"] = id_map[table["query_name"]]
            table["workbook"] = workbook
    return frappe.as_json(operations)


def repoint_filter_links(copies: dict):
    """Point each dashboard filter link that names an original at the copy its chart now reads.

    A link is followed only to a query the chart reads, and the chart's workbook
    now reads the copy.
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
    """Every (query, its workbook, source query) whose source is in another workbook.

    A source with no row is left out, because there is nothing to copy.
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


def copy_into(
    original: str, workbook: str, copies: dict, workbook_of: dict, stored: dict, copying: set | None = None
) -> str:
    """The copy of `original` in `workbook`, made the first time it is asked for.

    `stored` holds every query's operations before the patch changed any, so
    the copy reads the same originals `original` read, and each copy is keyed
    by its original. `copying` holds the copies being made, so a cycle of
    sources ends instead of recursing until the migrate stops.
    """
    copying = set() if copying is None else copying
    cycle = None
    if (original, workbook) in copies:
        return copies[(original, workbook)]

    source = frappe.get_doc(QUERY, original)
    operations = stored.get(original, source.operations)
    copying.add((original, workbook))
    id_map = {}
    for ref in referenced_queries(operations):
        if ref not in workbook_of or workbook_of[ref] == workbook:
            continue
        if (ref, workbook) in copying:
            # a cycle of sources, which never ran: the reference stays on the original
            cycle = ref
            continue
        id_map[ref] = copy_into(ref, workbook, copies, workbook_of, stored, copying)
    copying.discard((original, workbook))

    copy = frappe.new_doc(QUERY)
    copy.update(
        {
            "title": source.title,
            "workbook": workbook,
            "operations": rewrite_query_references(operations, id_map, workbook),
            "use_live_connection": source.use_live_connection,
            "is_script_query": source.is_script_query,
            "is_builder_query": source.is_builder_query,
            "is_native_query": source.is_native_query,
        }
    )
    for variable in source.variables:
        copy.append("variables", {"variable_name": variable.variable_name})
    # the value is mandatory, but the copy must not keep it
    copy.flags.ignore_mandatory = True
    # validate refuses the reference a cycle leaves on another workbook's query
    copy.flags.ignore_validate = bool(cycle)
    copy.insert(ignore_permissions=True)
    if source.variables:
        report_missing_values(copy, source)
    if cycle:
        report_cycle(copy, cycle)
    copies[(original, workbook)] = copy.name
    workbook_of[copy.name] = workbook
    return copy.name


def report_missing_values(copy, source) -> None:
    workbook_title, owner = frappe.db.get_value(WORKBOOK, copy.workbook, ["title", "owner"])
    data = {
        "query": copy.title or copy.name,
        "workbook": workbook_title or copy.workbook,
        "source_workbook": (frappe.db.get_value(WORKBOOK, source.workbook, "title") or source.workbook)
        if source.workbook
        else None,
        "variables": [variable.variable_name for variable in source.variables],
    }
    source_workbook = f'workbook "{data["source_workbook"]}"' if data["source_workbook"] else "no workbook"
    add_item(
        "P21",
        f'"{data["query"]}" in "{data["workbook"]}", copied from {source_workbook}: '
        f"enter its variables ({', '.join(data['variables'])}), which may be passwords and were not copied",
        reference=(QUERY, copy.name),
        user=None if owner == "Administrator" else owner,
        data=data,
    )


def report_cycle(copy, source: str) -> None:
    workbook_title, owner = frappe.db.get_value(WORKBOOK, copy.workbook, ["title", "owner"])
    data = {
        "query": copy.title or copy.name,
        "workbook": workbook_title or copy.workbook,
        "source": frappe.db.get_value(QUERY, source, "title") or source,
        "cycle": True,
    }
    add_item(
        "P21",
        f'"{data["query"]}" in "{data["workbook"]}": remove its source '
        f'"{data["source"]}", which reads it back. It could not run in Insights before 3.50 either.',
        reference=(QUERY, copy.name),
        user=None if owner == "Administrator" else owner,
        data=data,
    )
