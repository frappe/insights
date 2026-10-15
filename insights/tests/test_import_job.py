import json

import frappe

from insights.insights.doctype.insights_table_import_job.insights_table_import_job import JobState
from insights.tests.base import InsightsIntegrationTestCase

DATA_SOURCE = "Site DB"


class TestJobState(InsightsIntegrationTestCase):
    """The cursor must describe what is in the data store, not what a run intended."""

    def before_test(self):
        self.job = self.create_job("state_test_table")

    def create_job(self, table_name):
        if frappe.db.exists("Insights Table Import Job", table_name):
            frappe.delete_doc("Insights Table Import Job", table_name, force=True)

        doc = frappe.get_doc(
            {
                "doctype": "Insights Table Import Job",
                "title": table_name,
                "data_source": DATA_SOURCE,
                "table_name": table_name,
                "script": "pass",
                "state": json.dumps({"cursor": "2026-01-01"}),
            }
        )
        doc.flags.ignore_links = True
        doc.insert(ignore_permissions=True)
        return doc

    def stored_state(self):
        return json.loads(frappe.db.get_value("Insights Table Import Job", self.job.name, "state") or "{}")

    def test_setting_state_does_not_touch_the_job_row(self):
        state = JobState(self.job)
        state.set("cursor", "2026-08-13")

        self.assertEqual(state.get("cursor"), "2026-08-13")
        self.assertEqual(
            self.stored_state()["cursor"],
            "2026-01-01",
            "a run that fails after this point must start again from the old cursor",
        )

    def test_saving_state_writes_the_job_row(self):
        state = JobState(self.job)
        state.set("cursor", "2026-08-13")
        state.save()

        self.assertEqual(self.stored_state()["cursor"], "2026-08-13")

    def test_clear_and_delete_are_also_deferred(self):
        state = JobState(self.job)
        state.delete("cursor")
        state.clear()

        self.assertEqual(self.stored_state()["cursor"], "2026-01-01")

        state.save()
        self.assertEqual(self.stored_state(), {})

    def stored_table_name(self, job):
        return frappe.db.get_value("Insights Table Import Job", job.name, "table_name")

    def test_a_new_job_stores_a_scrubbed_table_name(self):
        job = self.create_job("Scrub Test Table")
        self.assertEqual(self.stored_table_name(job), "scrub_test_table")

    def test_saving_a_job_keeps_its_stored_table(self):
        job = self.create_job("keep_test_table")
        # a job saved before names were scrubbed on save
        frappe.db.set_value("Insights Table Import Job", job.name, "table_name", "Keep Test Table")
        job.reload()
        job.schedule = "0 * * * *"
        job.flags.ignore_links = True
        job.save(ignore_permissions=True)
        self.assertEqual(
            self.stored_table_name(job),
            "Keep Test Table",
            "the job's cursor describes the rows in that table",
        )
