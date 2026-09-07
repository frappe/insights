"""Move a `Insights Table v3` record on to another spelling of the table it names.

Every referrer names a table by the string the record stores, so a rename has to carry
the queries, the references, the links, the grants and the imported copy with it. See
`InsightsDataSourcev3.table_identity` for why the spelling changes at all.

`rename_tables` is the one entry point. It renames a record in place, or merges it into
the record that already holds the new name, and rewrites the referrers either way.
"""

import frappe

import insights
from insights.insights.doctype.insights_table_v3.insights_table_v3 import get_table_name

# How a person asked for the table to be imported. A merge keeps these whatever happens to
# the Data Store copy. Nothing else holds them, and only a person can type them again.
IMPORT_SETTINGS_FIELDS = (
    "sync_mode",
    "sync_from",
    "sync_cursor_column",
    "sync_primary_key_column",
    "sync_strategy",
    "row_limit",
    "before_import_script",
)
# The subset of the settings a person types. Only these say whether anyone configured the
# record — see `import_settings_are_untouched`.
TYPED_SETTINGS_FIELDS = (
    "sync_cursor_column",
    "sync_primary_key_column",
    "sync_from",
    "row_limit",
    "before_import_script",
)
# What the record says about its Data Store copy. These only hold once that copy moves.
WAREHOUSE_STATE_FIELDS = (
    "stored",
    "last_synced_on",
    "last_sync_bookmark",
)


def rename_tables(data_source: str, renames: dict[str, str]) -> None:
    """Apply `{old_table: new_table}` to `data_source`.

    The referrers are rewritten once for the whole batch: `update_queries` reads every
    query of the site, which is far too expensive to repeat per table.
    """
    applied = {}
    for old_table, new_table in renames.items():
        if old_table == new_table:
            continue
        if rename_table_record(data_source, old_table, new_table):
            applied[old_table] = new_table

    if not applied:
        return

    update_queries(data_source, applied)
    update_query_references(data_source, applied)
    update_table_links(data_source, applied)
    update_import_logs(data_source, applied)

    clear_permission_caches()


def clear_permission_caches() -> None:
    """Make the next permission check read the grants this rename moved.

    A rename gives the record a new key, and a team's allowed list holds keys. Two caches
    answer with the old one. `_get_allowed_resources_for_user` is cached for a day. It is
    built from `get_cached_doc("Insights Team", ...)`, which holds the grant rows
    themselves. `Insights Team.on_change` clears both, and nothing here saves a team.
    """
    from insights.insights.doctype.insights_team.insights_team import clear_cache

    # no name clears every team in one pass, so no team has to be read to be cleared
    frappe.clear_document_cache("Insights Team")
    clear_cache()


def rename_table_record(data_source: str, old_table: str, new_table: str) -> bool:
    """Move the record for `old_table` on to `new_table`. Returns False if there is none."""
    row = frappe.db.get_value(
        "Insights Table v3",
        {"data_source": data_source, "table": old_table},
        ["name", "table", "label", "stored"],
        as_dict=True,
    )
    if not row:
        return False

    new_name = get_table_name(data_source, new_table)
    if frappe.db.exists("Insights Table v3", new_name):
        merge_table(data_source, row, new_name, new_table)
        return True

    # renaming by hand rather than through `frappe.rename_doc`: every referrer is rewritten
    # below anyway, and this keeps the rename from touching the remote database, which is
    # routinely unreachable while `bench migrate` runs.
    frappe.db.set_value(
        "Insights Table v3",
        row.name,
        {
            "name": new_name,
            "table": new_table,
            # an untouched label is the table name; a label a person wrote is theirs
            "label": new_table if row.label == old_table else row.label,
        },
        update_modified=False,
    )
    frappe.db.set_value(
        "Insights Resource Permission",
        {"resource_type": "Insights Table v3", "resource_name": row.name},
        "resource_name",
        new_name,
        update_modified=False,
    )

    if row.stored and not rename_warehouse_table(data_source, old_table, new_table):
        # the imported data can no longer be found under the new name — let it re-import
        frappe.db.set_value("Insights Table v3", new_name, "stored", 0, update_modified=False)

    return True


def merge_table(data_source: str, row, survivor_name: str, new_table: str) -> None:
    """Fold `row` into the record that already holds `new_table`, then delete it.

    Both records name one remote table, so only one may stay `stored`. Two would import
    the same table twice per cycle and take the Data Store write lock twice.

    On a site the sync duplicated, `row` is the record that has been there all along and
    the survivor is the copy the sync made. So the survivor inherits the import — but only
    while nobody has configured it, because a person may have set up the duplicate instead.
    """
    survivor = frappe.db.get_value("Insights Table v3", survivor_name, ["stored", "label"], as_dict=True)
    inherit = not survivor.stored and import_settings_are_untouched(survivor_name)

    moved = False
    if inherit:
        settings = frappe.db.get_value("Insights Table v3", row.name, IMPORT_SETTINGS_FIELDS, as_dict=True)
        moved = bool(row.stored) and rename_warehouse_table(data_source, row.table, new_table)
        if moved:
            settings.update(
                frappe.db.get_value("Insights Table v3", row.name, WAREHOUSE_STATE_FIELDS, as_dict=True)
            )
        frappe.db.set_value("Insights Table v3", survivor_name, settings, update_modified=False)

    if row.stored and not moved:
        drop_warehouse_table(data_source, row.table)

    if row.label != row.table and survivor.label == new_table:
        # the same label rule as a rename: a label a person wrote is theirs
        frappe.db.set_value("Insights Table v3", survivor_name, "label", row.label, update_modified=False)

    move_grants(row.name, survivor_name)
    frappe.delete_doc("Insights Table v3", row.name, force=True, ignore_permissions=True)


def import_settings_are_untouched(name: str) -> bool:
    """True while nobody has said how this record imports.

    Only the typed fields answer this. `sync_mode` and `sync_strategy` mean nothing on
    their own. Incremental needs a cursor column, and its upsert strategy needs a primary
    key. A default read back from a blank document would not help either. The sync writes
    its records through `bulk_insert`, over a column list that names no sync field.
    """
    typed = frappe.db.get_value("Insights Table v3", name, TYPED_SETTINGS_FIELDS, as_dict=True)
    return not any(typed.values())


def move_grants(old_name: str, new_name: str) -> None:
    """Point the grants of `old_name` at `new_name`, dropping the ones already there.

    A grant is an `Insights Resource Permission` row a team holds against the record, and
    it carries that team's row restrictions. Deleting the rows instead would revoke the
    table from every team that reads it.
    """
    granted_to = frappe.get_all(
        "Insights Resource Permission",
        filters={"resource_type": "Insights Table v3", "resource_name": new_name},
        pluck="parent",
    )
    if granted_to:
        # a team that already reads the survivor would hold two rows saying one thing
        frappe.db.delete(
            "Insights Resource Permission",
            {
                "resource_type": "Insights Table v3",
                "resource_name": old_name,
                "parent": ["in", granted_to],
            },
        )

    frappe.db.set_value(
        "Insights Resource Permission",
        {"resource_type": "Insights Table v3", "resource_name": old_name},
        "resource_name",
        new_name,
        update_modified=False,
    )


def rename_warehouse_table(data_source: str, old_table: str, new_table: str) -> bool:
    from insights.insights.doctype.insights_data_source_v3.data_warehouse import (
        get_warehouse_schema_name,
        quote_identifier,
    )

    old_name = quote_identifier(frappe.scrub(old_table))
    new_name = quote_identifier(frappe.scrub(new_table))
    schema = get_warehouse_schema_name(data_source)
    try:
        with insights.warehouse.get_write_connection(schema) as db:
            db.raw_sql(f"ALTER TABLE {old_name} RENAME TO {new_name}")
        return True
    except Exception:
        return False


def drop_warehouse_table(data_source: str, table: str) -> None:
    """Drop the Data Store copy, but never let the Data Store block the rename.

    `WarehouseTable.drop` waits on the write lock. A Table Import holds that lock for its
    whole run. A rename that raised here would roll back the records it already moved. An
    undropped table is harmless, because `drop_orphan_warehouse_tables` collects it.
    """
    try:
        insights.warehouse.get_table(data_source, table).drop()
    except Exception:
        frappe.log_error(title=f"Failed to drop {table} of {data_source} from the data store")


def update_queries(data_source: str, renames: dict[str, str]) -> None:
    """Rewrite the table names referenced by the source/join/union operations of every query."""
    queries = frappe.get_all(
        "Insights Query v3",
        filters={"operations": ["like", "%table_name%"]},
        fields=["name", "operations"],
    )

    updates = {}
    for query in queries:
        operations = frappe.parse_json(query.operations)
        if not operations:
            continue

        if not rewrite_table_names(operations, data_source, renames):
            continue

        updates[query.name] = {"operations": frappe.as_json(operations)}

    frappe.db.bulk_update("Insights Query v3", updates, update_modified=False)


def rewrite_table_names(node, data_source: str, renames: dict[str, str]) -> bool:
    """Recursively rename every `{data_source, table_name}` reference. Returns True if changed."""
    changed = False

    if isinstance(node, list):
        for item in node:
            changed = rewrite_table_names(item, data_source, renames) or changed
        return changed

    if not isinstance(node, dict):
        return False

    if node.get("data_source") == data_source and node.get("table_name") in renames:
        node["table_name"] = renames[node["table_name"]]
        changed = True

    for value in node.values():
        changed = rewrite_table_names(value, data_source, renames) or changed

    return changed


def update_query_references(data_source: str, renames: dict[str, str]) -> None:
    rename_column_values("Insights Query Reference", data_source, "table_name", renames)


def update_import_logs(data_source: str, renames: dict[str, str]) -> None:
    """Keep the sync history, which `get_table_stats` reads by table name."""
    rename_column_values("Insights Table Import Log", data_source, "table_name", renames)


def update_table_links(data_source: str, renames: dict[str, str]) -> None:
    # a link can name a renamed table on either side, so each side is its own rewrite
    for field in ("left_table", "right_table"):
        rename_column_values("Insights Table Link v3", data_source, field, renames)


def rename_column_values(doctype: str, data_source: str, field: str, renames: dict[str, str]) -> None:
    """Rewrite `field` from every old name to its new one, in a single statement.

    Every row holding a given old name takes the same new one, so the rows themselves carry
    nothing a rename needs. `frappe.db.bulk_update` matches by document name, so it would
    have to read them all first — and an import log keeps a row per import forever.
    """
    table = frappe.qb.DocType(doctype)
    column = table[field]

    case = frappe.qb.terms.Case()
    for old_value, new_value in renames.items():
        case = case.when(column == old_value, new_value)

    (
        frappe.qb.update(table)
        .set(column, case)
        .where(table.data_source == data_source)
        .where(column.isin(list(renames)))
        .run()
    )
