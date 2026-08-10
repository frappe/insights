# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
import ipaddress
import re
import socket
from datetime import datetime
from urllib.parse import urlparse

import frappe
import pandas as pd
import requests
import telegram
from croniter import croniter
from frappe import _
from frappe.model.document import Document
from frappe.utils import validate_email_address
from frappe.utils.data import get_datetime, get_datetime_str, now_datetime
from requests.adapters import HTTPAdapter
from urllib3.connection import HTTPSConnection
from urllib3.connectionpool import HTTPSConnectionPool

from insights.insights.doctype.insights_data_source_v3.insights_data_source_v3 import (
    db_connections,
)
from insights.utils import deep_convert_dict_to_dict

# A hanging endpoint must not hold the scheduled job that sends every alert.
WEBHOOK_TIMEOUT_SECONDS = 10


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

        if self.channel == "Webhook":
            self.validate_webhook()

        try:
            self.evaluate_condition()
        except Exception as e:
            frappe.throw(f"Invalid condition: {e}")

    def validate_webhook(self):
        if not self.webhook_url:
            frappe.throw(_("Webhook URL is required for a webhook alert"))
        if not self.webhook_token:
            frappe.throw(_("Webhook token is required for a webhook alert"))
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
            "event": "insights_alert",
            "message": message,
            "context": {
                "alert": context["alert"]["title"],
                "query": context["query"]["title"],
                "count": context["count"],
                "rows": context["rows"],
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
        except (requests.RequestException, BlockedWebhookAddress) as e:
            frappe.log_error(
                message=frappe.get_traceback(),
                title=f"Insights webhook alert failed: {self.title}",
            )
            frappe.throw(_("Could not deliver the alert to {0}: {1}").format(self.webhook_url, str(e)))

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

    def evaluate_message(self, context=None):
        rows_pattern = r"{{\s*rows\s*}}"
        message_md = re.sub(rows_pattern, "{{ datatable }}", self.message)

        context = context or self.get_message_context()
        message_md = render_template_restricted(message_md, context)
        # A webhook consumer wants the text, not the styled email body.
        if self.channel in ("Telegram", "Webhook"):
            return message_md

        message_html = frappe.utils.md_to_html(message_md)
        return frappe.render_template(
            "insights/templates/alert.html", context=frappe._dict(message=message_html)
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
        try:
            alert_doc = frappe.get_cached_doc("Insights Alert", alert.name)
            if alert_doc.is_event_due():
                alert_doc.send_alert()
            frappe.db.commit()
        except Exception:
            frappe.db.rollback()
            frappe.log_error(title=f"Failed to send alert: {alert.name}")


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


def validate_public_url(url: str) -> None:
    """Reject a destination an Insights User should not be able to make this
    server talk to. Any Insights User can create an alert, so a webhook that
    resolves onto the server's own network reaches services that are not
    otherwise exposed to them. Only publicly routable hosts are delivery
    targets."""
    parsed = urlparse(url)
    if parsed.scheme != "https":
        frappe.throw(_("Webhook URL must use https"))
    if not parsed.hostname:
        frappe.throw(_("Webhook URL must include a hostname"))

    resolve_public_address(parsed.hostname, parsed.port or 443)


class BlockedWebhookAddress(frappe.ValidationError):
    pass


def resolve_public_address(hostname: str, port: int) -> str:
    """The one publicly routable address this hostname is allowed to be reached
    on. Returning the address, rather than approving the name, is what stops a
    second lookup from answering differently."""
    try:
        resolved = socket.getaddrinfo(hostname, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        frappe.throw(_("Could not resolve webhook host: {0}").format(hostname))

    for *_rest, sockaddr in resolved:
        address = ipaddress.ip_address(sockaddr[0])
        if address.version == 6 and address.ipv4_mapped:
            address = address.ipv4_mapped
        if not address.is_global:
            frappe.throw(
                _(
                    "Webhook URL resolves to a non-public address ({0}). "
                    "Alerts can only be sent to publicly routable hosts."
                ).format(address),
                exc=BlockedWebhookAddress,
            )
    return resolved[0][-1][0]


class _PublicOnlyConnection(HTTPSConnection):
    def _new_conn(self):
        pinned = resolve_public_address(self.host, self.port)
        original = self._dns_host
        self._dns_host = pinned
        try:
            return super()._new_conn()
        finally:
            self._dns_host = original


class _PublicOnlyConnectionPool(HTTPSConnectionPool):
    ConnectionCls = _PublicOnlyConnection


class PublicOnlyAdapter(HTTPAdapter):
    """Checks the address actually connected to, which DNS cannot change after the fact.

    A proxy resolves and connects on our behalf, so the destination cannot be
    checked here at all - proxied delivery is refused rather than trusted."""

    def init_poolmanager(self, *args, **kwargs):
        super().init_poolmanager(*args, **kwargs)
        self.poolmanager.pool_classes_by_scheme = {"https": _PublicOnlyConnectionPool}

    def proxy_manager_for(self, proxy, **proxy_kwargs):
        frappe.throw(
            _("Webhook alerts cannot be delivered through a proxy ({0})").format(proxy),
            exc=BlockedWebhookAddress,
        )


def post_to_public_url(url: str, data: str, headers: dict) -> requests.Response:
    """POST to a validated destination. A redirect is refused rather than
    followed, so the address that was checked is the address that receives the
    alert - configure the final URL instead."""
    validate_public_url(url)
    with requests.Session() as session:
        session.mount("https://", PublicOnlyAdapter())
        session.trust_env = False
        response = session.post(
            url,
            data=data,
            headers=headers,
            timeout=WEBHOOK_TIMEOUT_SECONDS,
            allow_redirects=False,
            proxies={},
        )
    if response.is_redirect:
        frappe.throw(_("Webhook URL must not redirect (got {0})").format(response.status_code))
    return response


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
