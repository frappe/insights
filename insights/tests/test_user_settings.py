"""Whose profile a user may write, and which language the UI speaks.

Both endpoints read the session rather than the request: `update_user` takes the
email it is given but refuses one that is not the caller's unless the caller is an
admin, and `get_translations` picks the caller's own language before the site's.
"""

from unittest.mock import patch

import frappe

from insights.api.translations import get_translations
from insights.api.user import update_user
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import delete_users
from insights.tests.permissions_utils import ADMIN, USER_1, USER_2, create_test_users


def name_of(email):
    user = frappe.get_doc("User", email)
    return (user.first_name, user.last_name)


class TestProfile(InsightsIntegrationTestCase):
    @classmethod
    def before_class(cls):
        create_test_users()

    @classmethod
    def after_class(cls):
        delete_users(USER_1, USER_2, ADMIN)

    # @feature settings.profile
    def test_a_user_writes_their_own_name_and_not_another_users(self):
        before = name_of(USER_2)

        with self.as_user(USER_1):
            update_user(USER_1, {"first_name": "Renamed", "last_name": "Themself"})

        self.assertEqual(name_of(USER_1), ("Renamed", "Themself"))

        with self.as_user(USER_1), self.assertRaises(frappe.PermissionError):
            update_user(USER_2, {"first_name": "Renamed", "last_name": "By Someone Else"})

        self.assertEqual(name_of(USER_2), before)


class TestTranslations(InsightsIntegrationTestCase):
    """Which language is asked for, not what the dictionary holds.

    The strings come from whichever translation files the site carries, so the
    rule under test is the language `get_translations` resolves to.
    """

    @classmethod
    def before_class(cls):
        create_test_users()

    @classmethod
    def after_class(cls):
        delete_users(USER_1, ADMIN)

    def before_test(self):
        self.site_language = frappe.db.get_single_value("System Settings", "language")
        self.addCleanup(frappe.db.set_single_value, "System Settings", "language", self.site_language)
        self.addCleanup(frappe.db.set_value, "User", USER_1, "language", None)

    def language_asked_for(self):
        with patch("insights.api.translations.get_all_translations") as get_all:
            get_all.return_value = {}
            get_translations()
        return get_all.call_args.args[0]

    # @feature settings.translations
    def test_the_ui_speaks_the_users_language_and_falls_back_to_the_sites(self):
        frappe.db.set_single_value("System Settings", "language", "fr")
        frappe.db.set_value("User", USER_1, "language", "de")

        with self.as_user(USER_1):
            self.assertEqual(self.language_asked_for(), "de")

        frappe.db.set_value("User", USER_1, "language", None)

        with self.as_user(USER_1):
            self.assertEqual(self.language_asked_for(), "fr")

        with self.as_user("Guest"):
            self.assertEqual(self.language_asked_for(), "fr")
