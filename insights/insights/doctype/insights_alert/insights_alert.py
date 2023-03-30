# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
import requests
from frappe.model.document import Document
from frappe.utils import validate_email_address
from frappe.utils.data import nowdate
from frappe.utils.safe_exec import get_safe_globals
from pandas import DataFrame


class InsightsAlert(Document):
    def validate(self):
        try:
            self.evaluate_condition(for_validate=True)
        except Exception as e:
            frappe.throw(f"Invalid condition: {e}")

    @frappe.whitelist()
    def send_alert(self):
        if self.channel == "Email":
            self.send_email_alert()
        if self.channel == "Telegram":
            self.send_telegram_alert()

    def send_telegram_alert(self):
        apiToken = frappe.db.get_single_value("Insights Settings", "telegram_api_token")
        chatID = self.telegram_chat_id
        apiURL = f"https://api.telegram.org/bot{apiToken}/sendMessage"
        message = f"Insights Alert: {self.title}"

        try:
            requests.post(apiURL, json={"chat_id": chatID, "text": message})
        except Exception:
            frappe.log_error("Insights Alert Error")
            raise

    def send_email_alert(self):
        if not self.evaluate_condition():
            return

        subject = f"Insights Alert: {self.title}"
        recievers = self.get_recipients()
        frappe.sendmail(
            recipients=recievers,
            subject=subject,
            now=True,
        )

    def evaluate_condition(self, for_validate=False):
        query = frappe.get_doc("Insights Query", self.query)
        result = (
            query.fetch_results()
            if not for_validate
            else frappe.parse_json(query.results)
        )

        if not result:
            return False

        result_dict = {}
        result_df = DataFrame(result[1:], columns=result[0])
        for col in result_df.columns:
            col_name = col.split("::")[0]
            result_dict[col_name] = result_df[col].tolist()

        return frappe.safe_eval(
            self.condition,
            None,
            eval_locals=frappe._dict(
                {
                    "result": result_dict,
                }
            ),
        )

    def get_recipients(self):
        recipients = self.recipients.split(",")
        for recipient in recipients:
            if not validate_email_address(recipient):
                frappe.throw(f"{recipient} is not a valid email address")
        return recipients
