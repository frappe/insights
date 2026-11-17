# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
"""Outbound HTTP to a URL that a user chose.

An Insights User is the least privileged role the app has, and it can already
save a webhook alert and press "send test". A URL from that form is therefore
an instruction to this server from an untrusted caller. A URL that resolves
onto the server's own network reaches databases, admin ports and metadata
services that the caller cannot otherwise touch, so only publicly routable
addresses are delivery targets.

Four rules hold that line:

- https only, so the payload and the destination stay confidential
- the address is checked again while the socket is opening, so a name that
  answers differently on a second lookup cannot slip past the first check
- a redirect is refused, so the address that was checked is the address that
  receives the body
- a proxy resolves and connects for us, which leaves nothing here to check, so
  this module ignores the environment's proxy settings and refuses a proxy a
  caller passes in

The last rule has a cost worth knowing: a deployment whose only route out is an
egress proxy cannot deliver. It hears so from the connection error below rather
than guessing.

Use this for any request whose URL came from a user. A fixed URL in the code
needs none of it.
"""

import ipaddress
import socket
from urllib.parse import urlparse

import frappe
import requests
from frappe import _
from requests.adapters import HTTPAdapter
from urllib3.connection import HTTPSConnection
from urllib3.connectionpool import HTTPSConnectionPool

# A hanging endpoint must not hold the scheduled job that serves every caller.
DEFAULT_TIMEOUT_SECONDS = 10


class OutboundRequestRefused(frappe.ValidationError):
    """Every refusal in this module, so one `except` covers them all."""


def validate_public_url(url: str) -> None:
    """Check what a URL says, without touching the network.

    Cheap and deterministic, so a form can call it on save. It does not check
    where the host resolves - that is `post_to_public_url`'s job, because an
    answer from save time tells you nothing about send time.
    """
    parsed = urlparse(url)
    if parsed.scheme != "https":
        frappe.throw(_("URL must use https"), exc=OutboundRequestRefused)
    if not parsed.hostname:
        frappe.throw(_("URL must include a hostname"), exc=OutboundRequestRefused)


def resolve_public_address(hostname: str, port: int) -> str:
    """The one publicly routable address this hostname may be reached on.

    Returning the address, rather than approving the name, is what stops a
    second lookup from answering differently.
    """
    try:
        resolved = socket.getaddrinfo(hostname, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        frappe.throw(_("Could not resolve host: {0}").format(hostname), exc=OutboundRequestRefused)

    for *_rest, sockaddr in resolved:
        address = ipaddress.ip_address(sockaddr[0])
        if address.version == 6 and address.ipv4_mapped:
            address = address.ipv4_mapped
        if not address.is_global:
            frappe.throw(
                _(
                    "{0} resolves to a non-public address ({1}). "
                    "Requests can only be sent to publicly routable hosts."
                ).format(hostname, address),
                exc=OutboundRequestRefused,
            )
    return resolved[0][-1][0]


class _PublicOnlyConnection(HTTPSConnection):
    def _new_conn(self):
        # `host` reads `_dns_host`, and urllib3 reads `host` again for SNI and
        # the certificate check after this returns. Restoring it is what keeps
        # the pin off the TLS handshake.
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
    """Checks the address actually connected to, which DNS cannot change afterwards."""

    def init_poolmanager(self, *args, **kwargs):
        super().init_poolmanager(*args, **kwargs)
        self.poolmanager.pool_classes_by_scheme = {"https": _PublicOnlyConnectionPool}

    def proxy_manager_for(self, proxy, **proxy_kwargs):
        # `post_to_public_url` already ignores the environment's proxies, so
        # arriving here means a caller passed one in. Refuse it too, rather
        # than leave the adapter unsafe for its next caller.
        frappe.throw(
            _("Requests cannot be sent through a proxy ({0})").format(proxy),
            exc=OutboundRequestRefused,
        )


def post_to_public_url(
    url: str,
    data: str,
    headers: dict,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> requests.Response:
    """POST to a publicly routable destination, or refuse and say why.

    The address check lives in the connection, not here, so there is one place
    that decides and it is the place that opens the socket.
    """
    validate_public_url(url)

    with requests.Session() as session:
        session.mount("https://", PublicOnlyAdapter())
        # Drops the environment's proxies, its CA bundle and its netrc
        # credentials. A user picks the host, so netrc could hand that host
        # this server's credentials for it.
        session.trust_env = False
        try:
            response = session.post(
                url,
                data=data,
                headers=headers,
                timeout=timeout,
                allow_redirects=False,
            )
        except requests.ConnectionError:
            frappe.throw(
                _(
                    "Could not reach {0}. Requests go out directly, never through a "
                    "proxy, so this server needs outbound access to the host."
                ).format(url),
                exc=OutboundRequestRefused,
            )

    if response.is_redirect:
        frappe.throw(
            _("{0} redirects ({1}). Configure the final URL instead.").format(url, response.status_code),
            exc=OutboundRequestRefused,
        )
    return response
