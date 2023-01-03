# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt


import frappe


def after_migrate():
    # if insights team named "Admin" doesn't exist, create it
    if not frappe.db.exists("Insights Team", "Admin"):
        insights_team = frappe.new_doc("Insights Team")
        insights_team.name = "Admin"
        insights_team.team_name = "Admin"
        insights_team.db_insert()
