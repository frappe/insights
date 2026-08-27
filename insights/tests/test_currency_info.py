from unittest.mock import patch

import frappe

from insights.api import get_currency_info, get_site_info
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import as_user


def _defaults(currency=None, hide_symbol=None):
    """Stand in for the two default reads get_currency_info makes, so a test
    states a site's currency without writing the shared site's defaults."""
    return (
        patch.object(frappe.db, "get_default", return_value=currency),
        patch.object(frappe.defaults, "get_global_default", return_value=hide_symbol),
    )


class TestCurrencyInfo(InsightsIntegrationTestCase):
    # two tests edit a Currency record to state a shape the site does not have
    SAVEPOINT = "test_currency_info"

    def test_symbol_comes_from_the_site_currency(self):
        currency, hidden = _defaults("USD")
        with currency, hidden:
            self.assertEqual(
                get_currency_info(),
                {"currency": "USD", "currency_symbol": "$", "currency_symbol_on_right": False},
            )

    def test_symbol_sits_on_the_right_when_the_currency_says_so(self):
        frappe.db.set_value("Currency", "SEK", "symbol_on_right", 1)
        currency, hidden = _defaults("SEK")
        with currency, hidden:
            info = get_currency_info()
        self.assertEqual(info["currency"], "SEK")
        self.assertTrue(info["currency_symbol_on_right"])

    def test_a_currency_without_a_symbol_prints_as_its_code(self):
        frappe.db.set_value("Currency", "XAF", "symbol", "")
        currency, hidden = _defaults("XAF")
        with currency, hidden:
            self.assertEqual(get_currency_info()["currency_symbol"], "XAF")

    def test_hide_currency_symbol_empties_the_symbol(self):
        currency, hidden = _defaults("INR", hide_symbol="1")
        with currency, hidden:
            info = get_currency_info()
        self.assertEqual(info["currency"], "INR")
        self.assertEqual(info["currency_symbol"], "")

    def test_a_site_without_a_currency_prints_amounts_bare(self):
        currency, hidden = _defaults(None)
        with currency, hidden, patch.object(frappe.db, "get_single_value", return_value=""):
            self.assertEqual(
                get_currency_info(),
                {"currency": None, "currency_symbol": "", "currency_symbol_on_right": False},
            )

    def test_a_guest_reading_a_public_dashboard_gets_the_symbol(self):
        # the guest whitelist is the point of the endpoint: a shared chart is
        # read by nobody in particular, and it still has to print its amounts
        self.assertIn(get_site_info, frappe.guest_methods)
        currency, hidden = _defaults("USD")
        with as_user("Guest"), currency, hidden:
            self.assertEqual(get_site_info()["currency_symbol"], "$")

    def test_the_client_can_reach_it_the_way_it_calls_it(self):
        # frappe-ui's `call` posts. An endpoint declared GET-only answers it
        # with a 403, and session.initialize() awaits this one - so restricting
        # the method here blanks the app rather than hardening anything.
        self.assertIn("POST", frappe.allowed_http_methods_for_whitelisted_func[get_site_info])
