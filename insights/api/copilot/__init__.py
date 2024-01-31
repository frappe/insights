# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe

from insights.decorators import check_role


@frappe.whitelist()
@check_role("Insights User")
def create_new_chat():
    empty_chat = frappe.db.exists("Insights Copilot Chat", {"copilot_bot": "Default"})
    if empty_chat:
        return empty_chat

    new_chat = frappe.new_doc("Insights Copilot Chat")
    new_chat.copilot_bot = "Default"
    new_chat.save()
    return new_chat.name
