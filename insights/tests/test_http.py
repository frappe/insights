# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
"""Tests for `insights.http`.

The point of the connect-time test below: `insights.http` reaches into private
urllib3 API to check the address a socket actually opens on. If a urllib3
upgrade renames `_new_conn`, the override binds to nothing, no error is raised,
and the rebinding defence quietly stops existing. Only a test that drives a
request all the way to the socket notices that.

Every test stubs DNS, so none of them touch the network.
"""

import socket
from unittest.mock import patch

from frappe.tests import UnitTestCase

from insights.http import (
    OutboundRequestRefused,
    PublicOnlyAdapter,
    post_to_public_url,
    resolve_public_address,
    validate_public_url,
)

PUBLIC = "93.184.216.34"


def addrinfo(*addresses: str) -> list:
    """What `socket.getaddrinfo` returns, for the addresses a test cares about."""
    entries = []
    for address in addresses:
        family = socket.AF_INET6 if ":" in address else socket.AF_INET
        sockaddr = (address, 443, 0, 0) if family == socket.AF_INET6 else (address, 443)
        entries.append((family, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", sockaddr))
    return entries


def resolving_to(*addresses: str):
    return patch("socket.getaddrinfo", return_value=addrinfo(*addresses))


class TestPublicUrlValidation(UnitTestCase):
    def test_http_is_refused(self):
        with self.assertRaises(OutboundRequestRefused):
            validate_public_url("http://example.com/hook")

    def test_scheme_without_hostname_is_refused(self):
        with self.assertRaises(OutboundRequestRefused):
            validate_public_url("https:///hook")

    def test_https_url_passes(self):
        validate_public_url("https://example.com/hook")

    def test_validation_does_not_resolve(self):
        """It runs inside a save, so it must not wait on a resolver."""
        with patch("socket.getaddrinfo") as getaddrinfo:
            validate_public_url("https://example.com/hook")
        getaddrinfo.assert_not_called()


class TestPublicAddressResolution(UnitTestCase):
    def test_public_address_is_returned(self):
        with resolving_to(PUBLIC):
            self.assertEqual(resolve_public_address("example.com", 443), PUBLIC)

    def test_loopback_is_refused(self):
        with resolving_to("127.0.0.1"), self.assertRaises(OutboundRequestRefused):
            resolve_public_address("example.com", 443)

    def test_private_range_is_refused(self):
        with resolving_to("10.0.0.1"), self.assertRaises(OutboundRequestRefused):
            resolve_public_address("example.com", 443)

    def test_link_local_metadata_address_is_refused(self):
        with resolving_to("169.254.169.254"), self.assertRaises(OutboundRequestRefused):
            resolve_public_address("example.com", 443)

    def test_ipv6_loopback_is_refused(self):
        with resolving_to("::1"), self.assertRaises(OutboundRequestRefused):
            resolve_public_address("example.com", 443)

    def test_ipv4_mapped_ipv6_is_unwrapped_before_the_check(self):
        with resolving_to("::ffff:127.0.0.1"), self.assertRaises(OutboundRequestRefused):
            resolve_public_address("example.com", 443)

    def test_one_private_answer_refuses_the_whole_name(self):
        """A name that answers with both is still a way onto the network."""
        with resolving_to(PUBLIC, "10.0.0.1"), self.assertRaises(OutboundRequestRefused):
            resolve_public_address("example.com", 443)

    def test_unresolvable_host_is_refused(self):
        with patch("socket.getaddrinfo", side_effect=socket.gaierror):
            with self.assertRaises(OutboundRequestRefused):
                resolve_public_address("nope.example.com", 443)


class TestPostToPublicUrl(UnitTestCase):
    def test_rebinding_is_refused_while_connecting(self):
        """The check that survives a lookup answering differently the second time.

        `validate_public_url` is stubbed to a pass, so nothing but the
        connection itself can refuse this. Match the message, not just the
        type: a socket that is merely unreachable also raises
        OutboundRequestRefused, so `assertRaises` alone stays green even after
        the urllib3 override comes unstuck.
        """
        with (
            patch("insights.http.validate_public_url"),
            # Nothing should get this far. If it does, fail here rather than
            # open a socket to whatever is listening on the test machine.
            patch("urllib3.util.connection.create_connection", side_effect=OSError),
            resolving_to("127.0.0.1"),
        ):
            with self.assertRaisesRegex(OutboundRequestRefused, "non-public address"):
                post_to_public_url("https://example.com/hook", data="{}", headers={})

    def test_a_proxy_is_refused(self):
        """A proxy connects for us, which leaves no address here to check."""
        with self.assertRaises(OutboundRequestRefused):
            PublicOnlyAdapter().proxy_manager_for("https://proxy.example.com:3128")
