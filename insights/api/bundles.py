# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""The authoring surface for standard content: "Export to app…" and "Duplicate".

Both ends of shipped content are authoring, not viewing, so they sit behind the
Insights role like the rest of the builder. Export refuses outside a
developer-mode bench — the machinery in `insights.bundle_export` enforces both,
whatever calls it. Duplicate is the other direction and runs on any site: it is
the only way to change shipped content, which is read-only once it lands.
"""

from insights import bundle_export, duplicate
from insights.decorators import insights_whitelist


@insights_whitelist()
def get_export_targets() -> dict:
    """The apps an export can go into, the bundles they already ship, and
    whether this bench allows exporting at all."""
    return bundle_export.export_targets()


@insights_whitelist()
def export_dashboard(
    dashboard: str, app: str, bundle: str | None = None, bundle_title: str | None = None
) -> dict:
    """Write a dashboard's closure into an app's bundle and flag it standard.

    `bundle` names the folder inside the app's `insights/` directory and
    defaults to the dashboard's logical name; `bundle_title` titles a bundle
    this export creates, and is ignored for one that already exists.
    """
    report = bundle_export.export_dashboard(dashboard, app, bundle=bundle, bundle_title=bundle_title)
    return report.as_dict()


@insights_whitelist()
def duplicate_dashboard(dashboard: str) -> dict:
    """Copy a dashboard's closure into a new workbook the caller owns.

    Two gates, two questions: the role here says the caller may author at all,
    the read check inside says they may have this dashboard.
    """
    return duplicate.duplicate_dashboard(dashboard)
