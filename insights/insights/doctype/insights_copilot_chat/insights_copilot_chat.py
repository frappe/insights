# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from random import randint

import frappe
from frappe.model.document import Document
from langchain.chat_models import ChatOpenAI
from langchain.schema import AIMessage, HumanMessage, SystemMessage

from insights.api.copilot import answer_with_bot


class InsightsCopilotChat(Document):
    def on_update(self):
        history = frappe.parse_json(self.history)
        if not history:
            return

        system_message = frappe.db.get_value(
            "Insights Copilot Bot", self.copilot_bot, "system_message"
        )
        answer = answer_with_bot(
            message=history[-1]["message"],
            system_message=system_message,
            data_source="Demo Data",
            history=history[:-1],
        )
        history.append(
            {
                "id": randint(1, 100000),
                "role": "assistant",
                "message": answer,
            }
        )
        self.history = frappe.as_json(history)
        self.db_set("history", self.history)
