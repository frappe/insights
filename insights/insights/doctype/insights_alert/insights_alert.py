# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
import re
from datetime import datetime

import frappe
import pandas as pd
import requests
import telegram
from croniter import croniter
from frappe import _
from frappe.model.document import Document
from frappe.utils import escape_html, get_url, validate_email_address
from frappe.utils.data import get_datetime, get_datetime_str, now_datetime

from insights.http import post_to_public_url, validate_public_url
from insights.insights.doctype.insights_data_source_v3.insights_data_source_v3 import (
    db_connections,
)
from insights.permission_user import permission_user
from insights.utils import deep_convert_dict_to_dict

# The payload is a contract with somebody else's code. Version it, so it can
# change without breaking every receiver that already parses it.
WEBHOOK_PAYLOAD_VERSION = 1

# A query with no ceiling on its rows must not become a POST with no ceiling on
# its body. `count` still reports the real total.
WEBHOOK_MAX_ROWS = 100


class InsightsAlert(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        channel: DF.Literal["Email", "Telegram", "Webhook"]
        condition: DF.Code
        cron_format: DF.Data | None
        custom_condition: DF.Check
        disabled: DF.Check
        frequency: DF.Literal["Hourly", "Daily", "Weekly", "Monthly", "Cron"]
        last_execution: DF.Datetime | None
        message: DF.MarkdownEditor | None
        permission_user: DF.Link | None
        query: DF.Link
        recipients: DF.SmallText | None
        telegram_chat_id: DF.Data | None
        title: DF.Data
        webhook_token: DF.Password | None
        webhook_url: DF.Data | None
    # end: auto-generated types

    def validate(self):
        if self.disabled:
            return

        if self.query:
            self.has_query_permission()

        if self.channel == "Email":
            self.get_recipients()

        if self.channel == "Webhook":
            self.validate_webhook()

        try:
            self.evaluate_condition()
        except Exception as e:
            frappe.throw(f"Invalid condition: {e}")

        self.set_permission_user()

    def set_permission_user(self):
        """Whoever enables the alert is who it runs as.

        The scheduler runs as Administrator, which passes every gate, and
        `validate` sees the query as it is at save. So the owner could point the
        query at a table they cannot read and have the next tick mail the rows
        out. Recording a user here moves the check to send time: the query runs
        under this user whatever it was changed to say.

        Only the enable transition writes it. Anyone with write on the alert's
        query may save the alert, so re-reading it on every save would let an
        edit as small as a title change hand the alert somebody else's row
        access, and mail the result to the list the alert already had.

        `permission_user` is permlevel 1 so no client can write it. Frappe
        resets permlevel fields before it runs `validate`, so this assignment is
        the one that lands.
        """
        if self.is_new() or self.has_value_changed("disabled"):
            self.permission_user = frappe.session.user

    def validate_webhook(self):
        if not self.webhook_url:
            frappe.throw(_("Webhook URL is required for a webhook alert"))
        if not self.webhook_token:
            frappe.throw(_("Webhook token is required for a webhook alert"))
        # Only what the URL says, not where it resolves. Resolving here would
        # put a name lookup inside the save transaction and still prove nothing
        # about send time. "Send test" is the button that answers that.
        validate_public_url(self.webhook_url)

    def has_query_permission(self):
        if not frappe.has_permission("Insights Query v3", "read", self.query):
            frappe.throw("You do not have permission to access this query")

    @frappe.whitelist()
    def send_alert(self, force: bool = False):
        results = self.evaluate_condition()
        if not results and not force:
            return

        # Built once: the context runs the query, and a webhook alert sends the
        # rendered message and the rows behind it.
        context = self.get_message_context()
        message = self.evaluate_message(context)

        if self.channel == "Email":
            self.send_email_alert(message)
        if self.channel == "Telegram":
            self.send_telegram_alert(message)
        if self.channel == "Webhook":
            self.send_webhook_alert(message, context)

        self.db_set("last_execution", now_datetime(), update_modified=False)

    def send_telegram_alert(self, message):
        tg = TelegramAlert(self.telegram_chat_id)
        tg.send(message)

    def send_webhook_alert(self, message, context):
        """POST the alert to the configured endpoint. The token travels in an
        Authorization header rather than the URI, which would put it in the
        receiver's access logs."""
        payload = {
            "version": WEBHOOK_PAYLOAD_VERSION,
            "event": "insights_alert",
            "message": message,
            "context": {
                "alert": context["alert"]["title"],
                "query": context["query"]["title"],
                "count": context["count"],
                "rows": context["rows"][:WEBHOOK_MAX_ROWS],
                "truncated": context["count"] > WEBHOOK_MAX_ROWS,
                "triggered_at": get_datetime_str(now_datetime()),
            },
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.get_password('webhook_token')}",
        }

        try:
            # frappe.as_json, not requests' json=: query rows carry datetimes
            # and Decimals that the plain encoder refuses.
            response = post_to_public_url(
                self.webhook_url,
                data=frappe.as_json(payload),
                headers=headers,
            )
            response.raise_for_status()
        except requests.HTTPError as e:
            frappe.throw(
                _("The webhook at {0} returned {1}").format(self.webhook_url, e.response.status_code)
            )
        except requests.RequestException as e:
            # No log_error here: `send_alerts` logs, and the interactive caller
            # reads the message. An OutboundRequestRefused already says what it
            # refused, so it goes up untouched.
            frappe.throw(
                _("Could not deliver the alert to {0} ({1})").format(self.webhook_url, type(e).__name__)
            )

    def get_author_email(self):
        """The address a reply reaches.

        `owner` is a User name, which is an address for an account created from
        an invite and the literal "Administrator" for the admin. `sendmail`
        refuses a reply_to it cannot parse, so an author it cannot resolve
        leaves the mail without one rather than unsent.
        """
        email = frappe.db.get_value("User", self.owner, "email")
        return email if email and validate_email_address(email) else None

    def send_email_alert(self, message):
        """Mail the alert, marked as one.

        The body is written by whoever owns the alert and leaves on the site's
        default outgoing account, so the mail names the alert that produced it
        and answers to its author rather than to the site.
        """
        frappe.sendmail(
            recipients=self.get_recipients(),
            subject=f"Insights Alert: {self.title}",
            message=message,
            reply_to=self.get_author_email(),
            now=True,
        )

    def evaluate_condition(self):
        doc = frappe.get_doc("Insights Query v3", self.query)
        with db_connections():
            return doc.evaluate_alert_expression(self.condition)

    def evaluate_message(self, context):
        rows_pattern = r"{{\s*rows\s*}}"
        message_md = re.sub(rows_pattern, "{{ datatable }}", self.message)

        message_md = render_template_restricted(message_md, context)
        # A webhook consumer wants the text, not the styled email body.
        if self.channel in ("Telegram", "Webhook"):
            return message_md

        message_html = frappe.utils.md_to_html(message_md)
        return frappe.render_template(  # nosemgrep - the template is a file in this app
            "insights/templates/alert.html",
            context=frappe._dict(
                message=message_html,
                # The template renders without autoescaping, so a value
                # interpolated into it is escaped here.
                alert=escape_html(self.title),
                author=escape_html(self.get_author_email() or self.owner),
                site_url=get_url(allow_header_override=False),
            ),
        )

    def get_message_context(self):
        doc = frappe.get_doc("Insights Query v3", self.query)
        with db_connections():
            data = doc.execute()

        rows = data["rows"]
        datatable = pd.DataFrame(rows).to_html(index=False)
        datatable = f"<div class='datatable-container'>{datatable}</div>"
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
                "datatable": datatable,
            }
        )

    def get_recipients(self):
        """The addresses this alert mails.

        Read at save as well as at send. `send_alerts` turns a send-time error
        into an Error Log entry and marks the alert as run, so an address
        checked only at send fails where nobody is looking.
        """
        recipients = [address.strip() for address in (self.recipients or "").split(",") if address.strip()]
        if not recipients:
            frappe.throw(_("An email alert needs at least one recipient"))

        for recipient in recipients:
            if not validate_email_address(recipient):
                frappe.throw(_("{0} is not a valid email address").format(recipient))

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
    alerts = frappe.get_all("Insights Alert", filters={"disabled": 0}, fields=["name", "permission_user"])
    for alert in alerts:
        try:
            alert_doc = frappe.get_cached_doc("Insights Alert", alert.name)
            if alert_doc.is_event_due():
                # the scheduler runs as Administrator, so without this the alert
                # would read every row of every table it names
                with permission_user(alert.permission_user):
                    alert_doc.send_alert()
            frappe.db.commit()
        except Exception:
            frappe.db.rollback()
            frappe.log_error(title=f"Failed to send alert: {alert.name}")
            record_execution(alert.name)


def record_execution(name: str):
    """Mark an alert as run, whether or not it delivered.

    `last_execution` is the cron's start point, so leaving it unset after a
    failure makes the alert due again on the next four-minute tick. A webhook
    pointed at an endpoint that is down would be retried forever, several
    hundred times a day, against somebody else's server. The alert ran. The
    next attempt belongs in the next scheduled window.

    This runs after the rollback above, so it needs its own commit.
    """
    frappe.db.set_value("Insights Alert", name, "last_execution", now_datetime(), update_modified=False)
    # The caller rolled back the failed alert. Without a commit of its own this
    # write goes out with the next one, or with nothing at all.
    frappe.db.commit()  # nosemgrep


class TelegramAlert:
    def __init__(self, chat_id):
        self.token = frappe.get_single("Insights Settings").get_password("telegram_api_token")
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


def render_template_restricted(template: str, context: dict) -> str:
    """Render a Jinja template with a restricted sandbox environment.

    Only allows access to explicitly passed context variables and basic filters.
    Does not expose frappe utilities or other globals.

    Uses the same sandboxed environment as frappe.render_template but without
    the get_safe_globals() that would expose frappe internals.
    """
    try:
        from frappe.utils.jinja import _get_jenv

        base_jenv = _get_jenv()
        jenv = base_jenv.overlay()
        jenv.filters = base_jenv.filters.copy()

    except ImportError:
        # fallback for v15
        from frappe.utils.jinja import get_jenv

        jenv = get_jenv()

    compiled_template = jenv.from_string(template)
    return compiled_template.render(context)
