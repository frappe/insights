# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from random import randint

import frappe
from frappe.model.document import Document

from insights.api.copilot.copilot import SQLCopilot


class InsightsCopilotChat(Document):
    def on_update(self):
        history = frappe.parse_json(self.history)
        if not history:
            return

        copilot = SQLCopilot(data_source="Demo Data", chat_history=history[:-1], verbose=True)
        last_message = history[-1]["message"]
        answer = copilot.ask(question=last_message, stream=True)
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
