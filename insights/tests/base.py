import frappe
from frappe.tests import IntegrationTestCase

from insights.tests.factories import as_user, is_visible


class InsightsIntegrationTestCase(IntegrationTestCase):
    SAVEPOINT = None
    COMMIT_AFTER_CLASS_SETUP = True
    COMMIT_AFTER_CLASS_TEARDOWN = True
    COMMIT_AFTER_TEST_SETUP = False
    COMMIT_AFTER_TEST_TEARDOWN = False

    @classmethod
    def before_class(cls):
        pass

    @classmethod
    def after_class(cls):
        pass

    def before_test(self):
        pass

    def after_test(self):
        pass

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with as_user("Administrator"):
            cls.before_class()
            if cls.COMMIT_AFTER_CLASS_SETUP:
                frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        try:
            with as_user("Administrator"):
                cls.after_class()
                if cls.COMMIT_AFTER_CLASS_TEARDOWN:
                    frappe.db.commit()
        finally:
            super().tearDownClass()

    def setUp(self):
        super().setUp()
        self.original_user = frappe.session.user
        self.addCleanup(frappe.set_user, self.original_user)
        frappe.set_user("Administrator")
        self.before_test()
        if self.SAVEPOINT:
            frappe.db.savepoint(self.SAVEPOINT)
        elif self.COMMIT_AFTER_TEST_SETUP:
            frappe.db.commit()

    def tearDown(self):
        try:
            frappe.set_user("Administrator")
            if self.SAVEPOINT:
                frappe.db.rollback(save_point=self.SAVEPOINT)
            self.after_test()
            if self.COMMIT_AFTER_TEST_TEARDOWN and not self.SAVEPOINT:
                frappe.db.commit()
        finally:
            super().tearDown()

    def as_user(self, user):
        return as_user(user)

    def set_team_permissions(self, enabled):
        """Turn `enable_permissions` on or off for one test.

        The setting scopes data sources and tables to teams. It has never scoped
        a workbook's contents, so a rule over those has to hold either way. The
        allowed-resource lookup is site-cached, so the cache goes with it.
        """
        from insights.insights.doctype.insights_team.insights_team import clear_cache

        original = frappe.db.get_single_value("Insights Settings", "enable_permissions")
        frappe.db.set_single_value("Insights Settings", "enable_permissions", enabled)
        clear_cache()
        self.addCleanup(clear_cache)
        self.addCleanup(frappe.db.set_single_value, "Insights Settings", "enable_permissions", original)

    def descriptions(self, result):
        """The `description` column of a result, sorted.

        The test tables carry one text column, so a sorted list of it is how
        these suites compare the rows a read returned.
        """
        return sorted(row["description"] for row in result["rows"])

    def assert_visible_to(self, user, doctype, name, message=None):
        with self.as_user(user):
            self.assertTrue(
                is_visible(doctype, name),
                message or f"{doctype} {name} should be visible to {user}",
            )

    def assert_not_visible_to(self, user, doctype, name, message=None):
        with self.as_user(user):
            self.assertFalse(
                is_visible(doctype, name),
                message or f"{doctype} {name} should not be visible to {user}",
            )
