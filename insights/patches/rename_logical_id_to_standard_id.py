import frappe
from frappe.model.utils.rename_field import rename_field

from insights.bundles import CHART, DASHBOARD, QUERY, WORKBOOK

# every doctype that carries the identity of shipped content
IDENTIFIED = (WORKBOOK, QUERY, CHART, DASHBOARD)


def execute():
    """Carry the identity field over to the name that states its rule.

    `logical_id` said what the field is not. Only standard content has one, so
    `standard_id` says the rule, and Standard ID is the term the glossary
    ratified.

    Guarded, because the old column is the exception rather than the rule: no
    release has shipped it to a site, so it exists only on a bench that migrated
    while the branch was in flight. `rename_field` copies the values into the
    column model sync has already added, which is why this is a post-model-sync
    patch.

    It runs before the two patches that write and read the field, so both of
    them speak the new name and neither has to know the old one existed.
    """
    for doctype in IDENTIFIED:
        if frappe.db.has_column(doctype, "logical_id"):
            rename_field(doctype, "logical_id", "standard_id")
