from unittest.mock import patch

import frappe

from insights.api import get_currency_info, get_site_info
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import as_user
from insights.utils import get_currency_symbols


def _defaults(currency=None, hide_symbol=None):
    """Stand in for the two default reads `get_currency_info` and `get_currency_symbols`
    make, so a test states a site's currency without writing the shared site's defaults."""
    return (
        patch.object(frappe.db, "get_default", return_value=currency),
        patch.object(frappe.defaults, "get_global_default", return_value=hide_symbol),
    )


class TestCurrencyInfo(InsightsIntegrationTestCase):
    # tests edit Currency records to state a shape the site does not have
    SAVEPOINT = "test_currency_info"

    def test_the_session_starts_with_the_site_currency_and_its_symbol(self):
        currency, hidden = _defaults("USD")
        with currency, hidden:
            self.assertEqual(
                get_currency_info(),
                {"currency": "USD", "currency_symbols": {"USD": {"symbol": "$", "symbol_on_right": False}}},
            )

    def test_a_symbol_is_looked_up_by_the_code_a_result_carries(self):
        # a disabled currency resolves like an enabled one
        frappe.db.set_value("Currency", "SEK", {"enabled": 0, "symbol_on_right": 1})
        _, hidden = _defaults()
        with hidden:
            symbols = get_currency_symbols(["INR", "SEK"])
        self.assertEqual(symbols["INR"]["symbol"], "₹")
        self.assertEqual(symbols["SEK"], {"symbol": "kr", "symbol_on_right": True})

    def test_a_currency_without_a_symbol_prints_as_its_code(self):
        frappe.db.set_value("Currency", "XAF", "symbol", "")
        _, hidden = _defaults()
        with hidden:
            self.assertEqual(get_currency_symbols(["XAF"])["XAF"]["symbol"], "XAF")

    def test_a_code_with_no_currency_row_prints_as_itself(self):
        # a CSV value has no Currency row, and the amount still prints
        _, hidden = _defaults()
        with hidden:
            self.assertEqual(
                get_currency_symbols(["High"])["High"], {"symbol": "High", "symbol_on_right": False}
            )

    def test_a_null_code_is_skipped(self):
        _, hidden = _defaults()
        with hidden:
            self.assertEqual(get_currency_symbols([None, ""]), {})

    def test_hide_currency_symbol_empties_every_lookup(self):
        currency, hidden = _defaults("INR", hide_symbol="1")
        with currency, hidden:
            self.assertEqual(get_currency_info(), {"currency": "INR", "currency_symbols": {}})
            self.assertEqual(get_currency_symbols(["USD"]), {})

    def test_a_site_without_a_currency_has_none_to_assume(self):
        currency, hidden = _defaults(None)
        with currency, hidden, patch.object(frappe.db, "get_single_value", return_value=""):
            self.assertEqual(get_currency_info(), {"currency": None, "currency_symbols": {}})

    def test_a_guest_reading_a_public_dashboard_gets_the_symbol(self):
        # the guest whitelist is the point of the endpoint: a shared chart is
        # read by nobody in particular, and it still has to print its amounts
        self.assertIn(get_site_info, frappe.guest_methods)
        currency, hidden = _defaults("USD")
        with as_user("Guest"), currency, hidden:
            self.assertEqual(get_site_info()["currency_symbols"]["USD"]["symbol"], "$")

    def test_the_client_can_reach_it_the_way_it_calls_it(self):
        # frappe-ui's `call` posts. An endpoint declared GET-only answers it
        # with a 403, and session.initialize() awaits this one - so restricting
        # the method here blanks the app rather than hardening anything.
        self.assertIn("POST", frappe.allowed_http_methods_for_whitelisted_func[get_site_info])
