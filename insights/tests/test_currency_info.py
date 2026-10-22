from unittest.mock import patch

import frappe

from insights.api import get_currency_info, get_site_info
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import as_user
from insights.utils import get_currencies


def _defaults(currency=None, hide_symbol=None):
    """Stand in for the two default reads `get_currency_info` and `get_currencies`
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
                {
                    "currency": "USD",
                    "currency_symbols": {
                        "USD": {"symbol": "$", "symbol_on_right": False, "number_format": ""}
                    },
                },
            )

    def test_a_symbol_is_looked_up_by_the_code_a_result_carries(self):
        # a disabled currency resolves like an enabled one
        frappe.db.set_value("Currency", "SEK", {"enabled": 0, "symbol_on_right": 1})
        _, hidden = _defaults()
        with hidden:
            symbols = get_currencies(["INR", "SEK"])
        self.assertEqual(symbols["INR"]["symbol"], "₹")
        self.assertEqual(symbols["SEK"], {"symbol": "kr", "symbol_on_right": True, "number_format": ""})

    def test_a_currency_number_format_is_sent_under_the_flag_desk_reads_it_under(self):
        frappe.db.set_value("Currency", "INR", "number_format", "#,##,###.##")
        frappe.db.set_value("Currency", "SEK", "number_format", "")
        _, hidden = _defaults()
        with hidden:
            self.assertEqual(get_currencies(["INR"])["INR"]["number_format"], "")

            frappe.db.set_single_value("System Settings", "use_number_format_from_currency", 1)
            currencies = get_currencies(["INR", "SEK"])
        self.assertEqual(currencies["INR"]["number_format"], "#,##,###.##")
        # a currency that states none leaves the site's to apply
        self.assertEqual(currencies["SEK"]["number_format"], "")

    def test_a_currency_without_a_symbol_prints_as_its_code(self):
        frappe.db.set_value("Currency", "XAF", "symbol", "")
        _, hidden = _defaults()
        with hidden:
            self.assertEqual(get_currencies(["XAF"])["XAF"]["symbol"], "XAF")

    def test_a_code_with_no_currency_row_prints_as_itself(self):
        # a CSV value has no Currency row, and the amount still prints
        _, hidden = _defaults()
        with hidden:
            self.assertEqual(
                get_currencies(["High"])["High"],
                {"symbol": "High", "symbol_on_right": False, "number_format": ""},
            )

    def test_a_null_code_is_skipped(self):
        _, hidden = _defaults()
        with hidden:
            self.assertEqual(get_currencies([None, ""]), {})

    def test_hide_currency_symbol_empties_every_symbol_and_keeps_the_grouping(self):
        frappe.db.set_single_value("System Settings", "use_number_format_from_currency", 1)
        frappe.db.set_value("Currency", "INR", "number_format", "#,##,###.##")
        frappe.db.set_value("Currency", "USD", "number_format", "#,###.##")
        currency, hidden = _defaults("INR", hide_symbol="1")
        with currency, hidden:
            self.assertEqual(
                get_currency_info(),
                {
                    "currency": "INR",
                    "currency_symbols": {
                        "INR": {"symbol": "", "symbol_on_right": False, "number_format": "#,##,###.##"}
                    },
                },
            )
            self.assertEqual(
                get_currencies(["USD"]),
                {"USD": {"symbol": "", "symbol_on_right": False, "number_format": "#,###.##"}},
            )

    def test_a_site_without_a_currency_has_none_to_assume(self):
        currency, hidden = _defaults(None)
        with currency, hidden, patch.object(frappe.db, "get_single_value", return_value=""):
            self.assertEqual(get_currency_info(), {"currency": None, "currency_symbols": {}})

    def test_a_guest_reading_a_public_dashboard_gets_the_symbol(self):
        # the guest whitelist is the point of the endpoint: a shared chart is
        # read by nobody in particular, and it still has to print its amounts
        self.assertIn(get_site_info, frappe.guest_methods)
        frappe.db.set_single_value("System Settings", "number_format", "#,##,###.##")
        currency, hidden = _defaults("USD")
        with as_user("Guest"), currency, hidden:
            self.assertEqual(get_site_info()["currency_symbols"]["USD"]["symbol"], "$")
            self.assertEqual(get_site_info()["number_format"], "#,##,###.##")

    def test_the_client_can_reach_it_the_way_it_calls_it(self):
        # frappe-ui's `call` posts. An endpoint declared GET-only answers it
        # with a 403, and session.initialize() awaits this one - so restricting
        # the method here blanks the app rather than hardening anything.
        self.assertIn("POST", frappe.allowed_http_methods_for_whitelisted_func[get_site_info])
