import json

import frappe

from insights.api import get_security_update
from insights.tests.base import InsightsIntegrationTestCase


class TestSecurityUpdate(InsightsIntegrationTestCase):
    def before_test(self):
        self.cached = frappe.cache.get_value("changelog-update-info")
        self.running_version = frappe.get_attr("insights.__version__")

    def after_test(self):
        frappe.cache.set_value("changelog-update-info", self.cached)

    def cache_update_check(self, **release):
        """Stores what the framework's weekly `check_for_update` stores."""
        release = {
            "current_version": self.running_version,
            "available_version": "999.0.0",
            "org_name": "frappe",
            "app_name": "insights",
            "title": "Insights",
            "security_issues": 2,
            **release,
        }
        frappe.cache.set_value(
            "changelog-update-info", json.dumps({"major": [], "minor": [release], "patch": []})
        )

    # @feature settings.security-update-notice
    def test_a_newer_release_with_security_fixes_is_reported(self):
        self.cache_update_check()
        self.assertEqual(
            get_security_update(),
            {
                "current_version": self.running_version,
                "available_version": "999.0.0",
                "security_issues": 2,
                "advisories_url": "https://github.com/frappe/insights/security/advisories",
                "frappe_cloud_url": None,
            },
        )

    # @feature settings.security-update-notice
    def test_a_check_made_before_the_site_updated_is_not_reported(self):
        """Its issue count describes the version the site ran then."""
        self.cache_update_check(current_version="0.0.1")
        self.assertIsNone(get_security_update())

    # @feature settings.security-update-notice
    def test_a_release_without_security_fixes_is_not_reported(self):
        self.cache_update_check(security_issues=0)
        self.assertIsNone(get_security_update())

    # @feature settings.security-update-notice
    def test_a_check_from_a_framework_without_security_counts_is_not_reported(self):
        self.cache_update_check()
        cached = json.loads(frappe.cache.get_value("changelog-update-info"))
        del cached["minor"][0]["security_issues"]
        frappe.cache.set_value("changelog-update-info", json.dumps(cached))
        self.assertIsNone(get_security_update())
