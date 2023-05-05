# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
from datetime import datetime

import frappe
from croniter import croniter
from frappe.integrations.utils import make_post_request
from frappe.model.document import Document
from frappe.utils import validate_email_address
from frappe.utils.data import get_datetime, get_datetime_str, now_datetime
from pandas import DataFrame


class InsightsAlert(Document):
    def validate(self):
        try:
            self.evaluate_condition(for_validate=True)
        except Exception as e:
            frappe.throw(f"Invalid condition: {e}")

    @frappe.whitelist()
    def send_alert(self):
        if not self.evaluate_condition():
            return
        if self.channel == "Email":
            self.send_email_alert()
        if self.channel == "Telegram":
            self.send_telegram_alert()
        self.db_set("last_execution", now_datetime(), update_modified=False)

    def send_telegram_alert(self):
        apiToken = frappe.get_single("Insights Settings").get_password(
            "telegram_api_token"
        )
        if not apiToken:
            frappe.throw("Telegram API Token not set in Insights Settings")

        chatID = self.telegram_chat_id
        message = f"Insights Alert: {self.title}"
        payload = {"chat_id": chatID, "text": message}
        apiURL = f"https://api.telegram.org/bot{apiToken}/sendMessage"

        try:
            make_post_request(
                apiURL,
                data=frappe.as_json(payload),
                headers={"Content-Type": "application/json"},
            )
        except Exception:
            frappe.log_error("Insights Alert Error")
            raise

    def send_email_alert(self):
        subject = f"Insights Alert: {self.title}"
        recievers = self.get_recipients()
        message = self.evaluate_message()
        frappe.sendmail(
            recipients=recievers,
            subject=subject,
            message=message,
            now=True,
        )

    def evaluate_condition(self, for_validate=False):
        query = frappe.get_doc("Insights Query", self.query)
        results = (
            query.fetch_results()
            if not for_validate
            else frappe.parse_json(query.results)
        )

        if not results:
            return False

        result_dict = {}
        result_df = query.get_results_df(results)
        for column in result_df.columns:
            result_dict[column] = result_df[column].tolist()

        return frappe.safe_eval(
            self.condition, eval_locals=frappe._dict(results=result_dict)
        )

    def evaluate_message(self):
        query = frappe.get_doc("Insights Query", self.query)
        query_dict = query.as_dict()
        query_dict.results = f"""<div class="results">{query.get_formatted_results(as_html=True)}</div>"""
        message = frappe.render_template(self.message, context=query_dict)
        return frappe.render_template(
            "insights/templates/alert.html", context=frappe._dict(message=message)
        )

    def get_recipients(self):
        recipients = self.recipients.split(",")
        for recipient in recipients:
            if not validate_email_address(recipient):
                frappe.throw(f"{recipient} is not a valid email address")
        return recipients

    @property
    def next_execution(self):
        return get_datetime_str(self.get_next_execution())

    def get_next_execution(self):
        CRON_MAP = {
            "Monthly": "0 0 1 * *",
            "Weekly": "0 0 * * 0",
            "Daily": "0 0 * * *",
            "Hourly": "0 * * * *",
        }
        if not self.cron_format:
            self.cron_format = CRON_MAP[self.frequency]

        start_time = get_datetime(self.last_execution or datetime(2000, 1, 1))
        return croniter(self.cron_format, start_time).get_next(datetime)

    def is_event_due(self):
        if not self.last_execution:
            return True

        next_execution = self.get_next_execution()
        return next_execution <= now_datetime()


def send_alerts():
    alerts = frappe.get_all("Insights Alert", filters={"disabled": 0})
    for alert in alerts:
        alert_doc = frappe.get_cached_doc("Insights Alert", alert.name)
        if alert_doc.is_event_due():
            alert_doc.send_alert()
            frappe.db.commit()
