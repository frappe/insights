import json
from unittest.mock import patch

import frappe

from insights.api.data_store import profile_warehouse
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import create_user, delete_users
from insights.utils import create_execution_log

ADMIN = "warehouse-profile-admin@test.com"
ANALYST = "warehouse-profile-analyst@test.com"
QUERY = "warehouse-profile-test"
# slower than anything another suite logs, so it is the one query profiled
LOGGED_SECONDS = 10**6


def run_now(method, queue, timeout, job_id, deduplicate, **kwargs):
    frappe.get_attr(method)(**kwargs)
    return frappe._dict(id=job_id)


class WarehouseProfile(InsightsIntegrationTestCase):
    @classmethod
    def before_class(cls):
        cls.after_class()
        create_user(ADMIN, roles=["Insights User", "Insights Admin"])
        create_user(ANALYST, roles="Insights User")
        create_execution_log(
            "SELECT sum(range) FROM range(100000)",
            time_taken=LOGGED_SECONDS,
            query_name=QUERY,
            data_store=True,
        )

    @classmethod
    def after_class(cls):
        frappe.db.delete("Insights Query Execution Log", {"query": QUERY})
        delete_users(ADMIN, ANALYST)

    # @feature data-store.profile-warehouse
    def test_an_admin_profiles_the_slowest_data_store_query_into_a_private_file(self):
        with self.as_user(ADMIN), patch("frappe.enqueue", side_effect=run_now):
            file_name = profile_warehouse(limit=1, min_time=LOGGED_SECONDS)["file_name"]

        file = frappe.get_doc("File", {"file_name": file_name})
        self.addCleanup(file.delete, ignore_permissions=True)
        report = json.loads(file.get_content())

        self.assertTrue(file.is_private)
        self.assertEqual(file.owner, ADMIN)
        [entry] = report["queries"]
        self.assertEqual(entry["query"], QUERY)
        [run] = entry["runs"]
        self.assertIsNone(run["error"])
        self.assertGreater(run["operators"], 0)
        self.assertEqual(run["rows_scanned"], 100000)

    # @feature data-store.profile-warehouse
    def test_an_insights_user_cannot_profile_the_data_store(self):
        with self.as_user(ANALYST), patch("frappe.enqueue") as enqueue:
            self.assertRaises(frappe.PermissionError, profile_warehouse)
        enqueue.assert_not_called()
