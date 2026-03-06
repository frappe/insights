import json

import frappe

from insights.cache_utils import make_digest


def execute():
    if not frappe.db.exists("DocType", "Insights Query v3"):
        return

    if not frappe.db.has_column("Insights Query v3", "query_hash"):
        return

    batch_size = 100
    total = frappe.db.count("Insights Query v3", {"query_hash": ("is", "not set")})

    if not total:
        return

    processed = 0

    while processed < total:
        queries = frappe.get_all(
            "Insights Query v3",
            filters={"query_hash": ("is", "not set")},
            fields=["name", "operations"],
            limit=batch_size,
        )

        if not queries:
            break

        for query in queries:
            query_hash = compute_query_hash(query.operations)
            frappe.db.set_value(
                "Insights Query v3",
                query.name,
                "query_hash",
                query_hash,
                update_modified=False,
            )

        processed += len(queries)
        frappe.db.commit()

        if processed % 500 == 0:
            frappe.publish_realtime(
                "backfill_query_hash_progress",
                {"processed": processed, "total": total},
            )


def compute_query_hash(operations):
    if not operations:
        return make_digest("empty")

    try:
        ops = frappe.parse_json(operations)
        normalized = json.dumps(ops, sort_keys=True, separators=(",", ":"))
        return make_digest(normalized)
    except (json.JSONDecodeError, TypeError):
        return make_digest(operations)
