# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from random import randint

import frappe
from frappe.model.document import Document

from insights.api.copilot import SQLCopilot


class InsightsCopilotChat(Document):
    def on_update(self):
        history = frappe.parse_json(self.history)
        if not history:
            return

        copilot = SQLCopilot(
            data_source="Demo Data",
            history=history[:-1],
            verbose=True,
        )
        answer = copilot.ask(question=history[-1]["message"])
        self.last_message_id = history[-1]["id"]
        history.append(
            {
                "id": randint(1, 100000),
                "role": "assistant",
                "message": answer.strip(),
            }
        )
        self.history = frappe.as_json(history)
        self.db_set("history", self.history)
        self.reload()
