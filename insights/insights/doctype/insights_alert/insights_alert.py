# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
from datetime import datetime

import frappe
import telegram
from croniter import croniter
from frappe.model.document import Document
from frappe.utils import validate_email_address
from frappe.utils.data import get_datetime, get_datetime_str, now_datetime

from insights.insights.doctype.insights_data_source_v3.insights_data_source_v3 import (
    db_connections,
)
from insights.utils import deep_convert_dict_to_dict


class InsightsAlert(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        channel: DF.Literal["Email", "Telegram"]
        condition: DF.Code
        cron_format: DF.Data | None
        custom_condition: DF.Check
        disabled: DF.Check
        frequency: DF.Literal["Hourly", "Daily", "Weekly", "Monthly", "Cron"]
        last_execution: DF.Datetime | None
        message: DF.MarkdownEditor | None
        next_execution: DF.Datetime | None
        query: DF.Link
        recipients: DF.SmallText | None
        telegram_chat_id: DF.Data | None
        title: DF.Data
    # end: auto-generated types

    def validate(self):
        try:
            self.evaluate_condition()
        except Exception as e:
            frappe.throw(f"Invalid condition: {e}")

    @frappe.whitelist()
    def send_alert(self, force=False):
        results = self.evaluate_condition()
        if not results and not force:
            return

        message = self.evaluate_message()

        if self.channel == "Email":
            self.send_email_alert(message)
        if self.channel == "Telegram":
            self.send_telegram_alert(message)

        self.db_set("last_execution", now_datetime(), update_modified=False)

    def send_telegram_alert(self, message):
        tg = TelegramAlert(self.telegram_chat_id)
        tg.send(message)

    def send_email_alert(self, message):
        subject = f"Insights Alert: {self.title}"
        recievers = self.get_recipients()
        frappe.sendmail(
            recipients=recievers,
            subject=subject,
            message=message,
            now=True,
        )

    def evaluate_condition(self):
        doc = frappe.get_doc("Insights Query v3", self.query)
        with db_connections():
            return doc.evaluate_alert_expression(self.condition)

    def evaluate_message(self):
        context = self.get_message_context()
        message = frappe.render_template(self.message, context=context)
        if self.channel == "Telegram":
            return message

        return frappe.render_template(
            "insights/templates/alert.html", context=frappe._dict(message=message)
        )

    def get_message_context(self):
        doc = frappe.get_doc("Insights Query v3", self.query)
        with db_connections():
            data = doc.execute()
        rows = data["rows"]

        return deep_convert_dict_to_dict(
            {
                "rows": rows,
                "count": len(rows),
                "query": {
                    "title": doc.title,
                },
                "alert": {
                    "title": self.title,
                },
            }
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

    @frappe.whitelist()
    def test_alert(self):
        self.send_alert(force=True)


def send_alerts():
    alerts = frappe.get_all("Insights Alert", filters={"disabled": 0})
    for alert in alerts:
        alert_doc = frappe.get_cached_doc("Insights Alert", alert.name)
        if alert_doc.is_event_due():
            alert_doc.send_alert()
            frappe.db.commit()


class TelegramAlert:
    def __init__(self, chat_id):
        self.token = frappe.get_single("Insights Settings").get_password(
            "telegram_api_token"
        )
        if not self.token:
            frappe.throw("Telegram Bot Token not set in Insights Settings")

        self.chat_id = chat_id

    def send(self, message):
        try:
            return self.bot.send_message(chat_id=self.chat_id, text=message[:4096])
        except Exception:
            frappe.log_error("Telegram Bot Error")
            raise

    @property
    def bot(self):
        return telegram.Bot(token=self.token)
