# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""The authoring surface for bundles: "Export to app…".

Export is authoring, not viewing, so it sits behind the Insights role like the
rest of the builder, and refuses outside a developer-mode bench — the machinery
in `insights.bundle_export` enforces both, whatever calls it.
"""

from insights import bundle_export
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
