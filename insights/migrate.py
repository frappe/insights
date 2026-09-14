# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt


import frappe

# A shipped template's copy is compared against the fingerprint taken when it was
# imported, and a migration that rewrites anything `export()` carries moves that
# fingerprint, so every imported copy would read as edited and never take another
# update. The copies are read once before any patch writes and re-stamped once
# after they all have, so no patch has to remember.
PRISTINE_COPIES = "insights_pristine_template_copies"


def before_migrate():
    try:
        from insights.api.templates import pristine_template_copies

        frappe.flags[PRISTINE_COPIES] = pristine_template_copies()
    except Exception:
        # no copy is known pristine, which is not the same answer as none being
        # pristine — `after_migrate` reads the difference
        frappe.flags[PRISTINE_COPIES] = None
        frappe.log_error(title="Error reading pristine template copies")


def after_migrate():
    try:
        create_admin_team()
    except Exception:
        frappe.log_error(title="Error creating Admin Team")

    # A read that failed knows no copy to be pristine. Re-stamping that answer
    # would stamp none of them, and every copy the patches rewrote would read as
    # edited from then on, with no way back. So the whole update is skipped and
    # the next migrate, which reads the copies before it writes, does it. An
    # install runs this hook without the read, and has no copy to re-stamp.
    pristine = frappe.flags.pop(PRISTINE_COPIES, [])
    if pristine is None:
        return

    # before the sync below, which only updates a copy that still reads as pristine
    try:
        from insights.api.templates import restamp_template_copies

        restamp_template_copies(pristine)
    except Exception:
        frappe.log_error(title="Error re-stamping template copies")

    try:
        from insights.api.templates import sync_workbook_template_updates

        sync_workbook_template_updates()
    except Exception:
        frappe.log_error(title="Error syncing workbook template updates")


def create_admin_team():
    if not frappe.db.exists("Insights Team", "Admin"):
        frappe.get_doc(
            {
                "doctype": "Insights Team",
                "team_name": "Admin",
                "team_members": [{"user": "Administrator"}],
            }
        ).insert(ignore_permissions=True)
