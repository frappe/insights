# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import add_days, now_datetime


def create_daily_snapshots():
    workbooks = frappe.get_all(
        "Insights Workbook",
        filters={"enable_snapshots": 1},
        fields=["name", "title"],
    )

    for workbook in workbooks:
        try:
            workbook_doc = frappe.get_doc("Insights Workbook", workbook.name)
            snapshot_name = workbook_doc.save_snapshot()
            if snapshot_name:
                frappe.db.commit()
        except Exception:
            frappe.log_error(
                title=f"Failed to create snapshot for workbook {workbook.name}",
                message=frappe.get_traceback(),
            )


def delete_old_snapshots():
    cutoff_date = add_days(now_datetime(), -30)

    old_snapshots = frappe.get_all(
        "Insights Workbook Snapshot",
        filters=[["creation", "<", cutoff_date]],
        pluck="name",
    )

    for snapshot_name in old_snapshots:
        try:
            frappe.delete_doc(
                "Insights Workbook Snapshot",
                snapshot_name,
                ignore_permissions=True,
                force=True,
            )
        except Exception as e:
            frappe.log_error(
                title=f"Failed to delete snapshot {snapshot_name}",
                message=frappe.get_traceback(),
            )

    if old_snapshots:
        frappe.db.commit()
