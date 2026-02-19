# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
from datetime import datetime
import frappe
from croniter import croniter
from frappe.model.document import Document
from frappe.utils import validate_email_address, md_to_html
from frappe.utils.data import get_datetime, get_datetime_str, now_datetime
from pandas import DataFrame


class InsightsAlert(Document):
    def validate(self):

        if self.disabled:
            return

        if self.query:
            self.has_query_permission()

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
        message = self.evaluate_message()
        tg = Telegram(self.telegram_chat_id)
        tg.send(message)

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
            query.fetch_results() if not for_validate else query.retrieve_results()
        )

        if not results:
            return False

        column_names = [d.get("label") for d in results[0]]
        results = DataFrame(results[1:], columns=column_names)

        return frappe.safe_eval(
            self.condition, eval_locals=frappe._dict(results=results, any=any)
        )

    def has_query_permission(self):
        if not frappe.has_permission("Insights Query", "read", self.query):
            frappe.throw("You do not have permission to access this query")

    def evaluate_message(self):

        query = frappe.get_doc("Insights Query", self.query)
        context = query.as_dict()

        message_md = render_template_restricted(self.message, context)
        if self.channel == "Telegram":
            return message_md

        message_html = md_to_html(message_md)
        return frappe.render_template(
            "insights/templates/alert.html", context=frappe._dict(message=message_html)
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


def render_template_restricted(template: str, context: dict) -> str:
    """Render a Jinja template with a restricted sandbox environment.

    Only allows access to explicitly passed context variables and basic filters.
    Does not expose frappe utilities or other globals.

    Uses the same sandboxed environment as frappe.render_template but without
    the get_safe_globals() that would expose frappe internals.
    """
    from frappe.utils.jinja import _get_jenv

    base_jenv = _get_jenv()

    # Create an overlay to avoid modifying the cached instance
    jenv = base_jenv.overlay()

    # Copy filters but do NOT add get_safe_globals() or jinja hooks
    jenv.filters = base_jenv.filters.copy()

    compiled_template = jenv.from_string(template)
    return compiled_template.render(context)


class Telegram:
    def __init__(self, chat_id: str = None):
        self.token = frappe.get_single("Insights Settings").get_password(
            "telegram_api_token"
        )
        if not self.token:
            frappe.throw("Telegram Bot Token not set in Insights Settings")

        if chat_id:
            self.chat_id = chat_id

    def send(self, message):
        import telegram

        try:
            text = message[: telegram.MAX_MESSAGE_LENGTH]
            parse_mode = telegram.ParseMode.MARKDOWN
            return self.bot.send_message(
                chat_id=self.chat_id, text=text, parse_mode=parse_mode
            )
        except Exception:
            frappe.log_error("Telegram Bot Error")
            raise

    @property
    def bot(self):
        import telegram

        return telegram.Bot(token=self.token)
