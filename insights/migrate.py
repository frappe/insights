# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt


import click
import frappe


def after_migrate():
    try:
        create_admin_team()
    except Exception:
        frappe.log_error(title="Error creating Admin Team")

    try:
        from insights.api.templates import sync_workbook_template_updates

        sync_workbook_template_updates()
    except Exception:
        frappe.log_error(title="Error syncing workbook template updates")

    try:
        warn_about_the_templates_hook()
    except Exception:
        frappe.log_error(title="Error reading the insights_workbooks hook")


def apps_declaring_the_templates_hook() -> list[str]:
    """Installed apps other than Insights that ship workbook templates.

    Reading an app's hooks imports it, and an app that is installed but not
    importable would otherwise take the migrate down with it.
    """
    from insights.api.templates import TEMPLATES_HOOK

    apps = []
    for app in sorted(frappe.get_installed_apps()):
        if app == "insights":
            continue
        try:
            if frappe.get_hooks(TEMPLATES_HOOK, app_name=app):
                apps.append(app)
        except Exception:
            continue

    return apps


def warn_about_the_templates_hook() -> None:
    """Tell an app author their workbook templates stop being read.

    The hook and the library retire on `develop`; standard workbooks replace
    them. `click.secho` is how frappe's own migrate warns an app author, and it
    reads the same on every frappe version this branch supports —
    `frappe.utils.deprecations` does not exist past v15.
    """
    apps = apps_declaring_the_templates_hook()
    if not apps:
        return

    click.secho(
        f"{', '.join(apps)} declares the `insights_workbooks` hook, which is deprecated. "
        "Insights removes it in the next major version, and the workbook templates it "
        "points at stop being read. Ship the workbooks as standard documents instead.",
        fg="yellow",
    )


def create_admin_team():
    if not frappe.db.exists("Insights Team", "Admin"):
        frappe.get_doc(
            {
                "doctype": "Insights Team",
                "team_name": "Admin",
                "team_members": [{"user": "Administrator"}],
            }
        ).insert(ignore_permissions=True)
