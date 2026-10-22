from unittest.mock import patch

import frappe

from insights.api import get_currency_info, get_site_info
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import as_user
from insights.utils import get_currency_symbols


def _defaults(currency=None, hide_symbol=None, number_format=None):
    """Stand in for the default reads `get_site_info` makes, so a test states a site's
    currency and number format without writing the shared site's defaults."""
    site_defaults = {"currency": currency, "number_format": number_format}
    return (
        patch.object(frappe.db, "get_default", side_effect=lambda key, *_, **__: site_defaults.get(key)),
        patch.object(frappe.defaults, "get_global_default", return_value=hide_symbol),
    )


class TestCurrencyInfo(InsightsIntegrationTestCase):
    # tests edit Currency records to state a shape the site does not have
    SAVEPOINT = "test_currency_info"

    # @feature charts.measure-unit
    def test_the_session_starts_with_the_site_currency_and_its_symbol(self):
        currency, hidden = _defaults("USD")
        with currency, hidden:
            self.assertEqual(
                get_currency_info(),
                {
                    "currency": "USD",
                    "currency_symbols": {
                        "USD": {"symbol": "$", "symbol_on_right": False, "number_format": "#,###.##"}
                    },
                },
            )

    # @feature charts.measure-unit
    def test_a_symbol_is_looked_up_by_the_code_a_result_holds(self):
        # a disabled currency resolves like an enabled one
        frappe.db.set_value("Currency", "SEK", {"enabled": 0, "symbol_on_right": 1})
        _, hidden = _defaults()
        with hidden:
            symbols = get_currency_symbols(["INR", "SEK"])
        self.assertEqual(symbols["INR"]["symbol"], "₹")
        self.assertEqual(symbols["SEK"]["symbol"], "kr")
        self.assertTrue(symbols["SEK"]["symbol_on_right"])

    # @feature charts.currency-number-format
    def test_a_currency_carries_its_number_format(self):
        # an AED amount groups in millions on a site set to lakhs, as fmt_money does
        frappe.db.set_value("Currency", "AED", "number_format", "#,###.##")
        frappe.db.set_value("Currency", "INR", "number_format", "#,##,###.##")
        frappe.db.set_value("Currency", "SEK", "number_format", "")
        _, hidden = _defaults()
        with hidden:
            currencies = get_currency_symbols(["AED", "INR", "SEK", "High"])
        self.assertEqual(currencies["AED"]["number_format"], "#,###.##")
        self.assertEqual(currencies["INR"]["number_format"], "#,##,###.##")
        # empty leaves the site's to apply
        self.assertEqual(currencies["SEK"]["number_format"], "")
        self.assertEqual(currencies["High"]["number_format"], "")

    # @feature charts.measure-unit
    def test_a_currency_without_a_symbol_prints_as_its_code(self):
        frappe.db.set_value("Currency", "XAF", "symbol", "")
        _, hidden = _defaults()
        with hidden:
            self.assertEqual(get_currency_symbols(["XAF"])["XAF"]["symbol"], "XAF")

    # @feature charts.measure-unit
    def test_a_code_with_no_currency_row_prints_as_itself(self):
        # a CSV value has no Currency row, and the amount still prints
        _, hidden = _defaults()
        with hidden:
            self.assertEqual(
                get_currency_symbols(["High"])["High"],
                {"symbol": "High", "symbol_on_right": False, "number_format": ""},
            )

    # @feature charts.measure-unit
    def test_a_null_code_is_skipped(self):
        _, hidden = _defaults()
        with hidden:
            self.assertEqual(get_currency_symbols([None, ""]), {})

    # @feature charts.measure-unit
    def test_hide_currency_symbol_empties_every_symbol(self):
        frappe.db.set_value("Currency", "INR", "number_format", "#,##,###.##")
        currency, hidden = _defaults("INR", hide_symbol="1")
        with currency, hidden:
            self.assertEqual(get_currency_info()["currency_symbols"]["INR"]["symbol"], "")
            # the grouping stays: hiding the symbol is not hiding the currency
            self.assertEqual(get_currency_info()["currency_symbols"]["INR"]["number_format"], "#,##,###.##")
            self.assertEqual(get_currency_symbols(["USD"])["USD"]["symbol"], "")

    # @feature charts.measure-unit
    def test_a_site_without_a_currency_has_none_to_assume(self):
        currency, hidden = _defaults(None)
        with currency, hidden, patch.object(frappe.db, "get_single_value", return_value=""):
            self.assertEqual(get_currency_info(), {"currency": None, "currency_symbols": {}})

    # @feature shared.currency-for-guest
    def test_a_guest_reading_a_public_dashboard_gets_the_symbol(self):
        # the guest whitelist is the point of the endpoint: a shared chart is
        # read by nobody in particular, and it still has to print its amounts
        self.assertIn(get_site_info, frappe.guest_methods)
        currency, hidden = _defaults("USD")
        with as_user("Guest"), currency, hidden:
            self.assertEqual(get_site_info()["currency_symbols"]["USD"]["symbol"], "$")

    # @feature charts.currency-number-format
    def test_the_site_states_the_number_format_desk_groups_by(self):
        currency, hidden = _defaults("INR", number_format="#,##,###.##")
        with currency, hidden:
            self.assertEqual(get_site_info()["number_format"], "#,##,###.##")

    # @feature charts.measure-unit
    def test_the_client_can_reach_it_the_way_it_calls_it(self):
        # frappe-ui's `call` posts. An endpoint declared GET-only answers it
        # with a 403, and session.initialize() awaits this one - so restricting
        # the method here blanks the app rather than hardening anything.
        self.assertIn("POST", frappe.allowed_http_methods_for_whitelisted_func[get_site_info])
