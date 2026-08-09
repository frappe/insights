# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""The authoring surface for standard content: "Export to app…" and "Duplicate".

Both ends of shipped content are authoring, not viewing, so they sit behind the
Insights role like the rest of the builder. Export refuses outside a
developer-mode bench — the machinery in `insights.export_to_app` enforces both,
whatever calls it. Duplicate is the other direction and runs on any site: it is
the only way to change shipped content, which is read-only once it lands. The
gallery browses what a site was shipped and duplicates a shipped workbook whole;
the island duplicates one dashboard.
"""

from insights import duplicate, export_to_app, standard_content
from insights.decorators import insights_whitelist


@insights_whitelist()
def get_export_targets() -> dict:
    """The apps an export can go into, the workbooks they already ship, and
    whether this bench allows exporting at all."""
    return export_to_app.export_targets()


@insights_whitelist()
def export_dashboard(
    dashboard: str, app: str, folder: str | None = None, workbook_title: str | None = None
) -> dict:
    """Write a dashboard's closure into a workbook an app ships, and flag it standard.

    `folder` names the shipped workbook's folder inside the app's `insights/`
    directory and defaults to the dashboard's logical name; `workbook_title`
    titles a workbook this export creates, and is ignored for one that already
    exists.
    """
    report = export_to_app.export_dashboard(dashboard, app, folder=folder, workbook_title=workbook_title)
    return report.as_dict()


@insights_whitelist()
def duplicate_dashboard(dashboard: str) -> dict:
    """Copy a dashboard's closure into a new workbook the caller owns.

    Two gates, two questions: the role here says the caller may author at all,
    the read check inside says they may have this dashboard.
    """
    return duplicate.duplicate_dashboard(dashboard)


@insights_whitelist()
def get_standard_content() -> list[dict]:
    """The shipped workbooks this site has, for the gallery to browse."""
    return standard_content.gallery()


@insights_whitelist()
def duplicate_workbook(workbook: str) -> dict:
    """Copy a shipped workbook's dashboards into a new workbook the caller owns.

    The gallery's action, and the same two gates as `duplicate_dashboard`.
    """
    return duplicate.duplicate_workbook(workbook)
