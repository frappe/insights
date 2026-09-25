import json
import os
import tempfile

import frappe

from insights.insights.doctype.insights_table_import_job.insights_table_import_job import (
    JobState,
    TableImportJobRun,
)
from insights.tests.base import InsightsIntegrationTestCase

DATA_SOURCE = "Site DB"


def create_job(table_name):
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


class TestJobState(InsightsIntegrationTestCase):
    """The cursor must describe what is in the data store, not what a run intended."""

    def before_test(self):
        self.job = create_job("state_test_table")

    def stored_state(self):
        return json.loads(frappe.db.get_value("Insights Table Import Job", self.job.name, "state") or "{}")

    # @feature data-store.import-cursor
    def test_setting_state_does_not_touch_the_job_row(self):
        state = JobState(self.job)
        state.set("cursor", "2026-08-13")

        self.assertEqual(state.get("cursor"), "2026-08-13")
        self.assertEqual(
            self.stored_state()["cursor"],
            "2026-01-01",
            "a run that fails after this point must start again from the old cursor",
        )

    # @feature data-store.import-cursor
    def test_saving_state_writes_the_job_row(self):
        state = JobState(self.job)
        state.set("cursor", "2026-08-13")
        state.save()

        self.assertEqual(self.stored_state()["cursor"], "2026-08-13")

    # @feature data-store.import-cursor
    def test_clear_and_delete_are_also_deferred(self):
        state = JobState(self.job)
        state.delete("cursor")
        state.clear()

        self.assertEqual(self.stored_state()["cursor"], "2026-01-01")

        state.save()
        self.assertEqual(self.stored_state(), {})


class TestImportJobScript(InsightsIntegrationTestCase):
    def before_test(self):
        self.job = create_job("script_sandbox_table")
        self.addCleanup(frappe.delete_doc, "Insights Table Import Job", self.job.name, force=True)
        self.todo = frappe.get_doc({"doctype": "ToDo", "description": "import job"}).insert(
            ignore_permissions=True
        )
        self.addCleanup(frappe.delete_doc, "ToDo", self.todo.name, force=True)

    def run_script(self, script):
        run = TableImportJobRun(self.job.name)
        inserted, logged = [], []
        run.job.script = script
        run.data_source = frappe._dict(get_api_client=lambda: frappe._dict(fetch=lambda path: [{"n": 1}]))
        run._table_writer = frappe._dict(insert=inserted.append, name="script_sandbox_table")
        run.job_state = JobState(run.job)
        run._log = logged.append
        run._run_script()
        return inserted, logged, run.job_state

    # @feature data-store.import-script-sandbox
    def test_a_job_script_reads_calls_its_client_and_inserts(self):
        inserted, logged, state = self.run_script(
            "\n".join(
                [
                    "rows = client.fetch('/items')",
                    "state.set('cursor', frappe.utils.add_days('2026-01-01', 1))",
                    "table.insert(pandas.DataFrame(rows))",
                    f"log(frappe.get_doc('ToDo', '{self.todo.name}').description)",
                ]
            )
        )

        self.assertEqual(inserted[0].to_dict(orient="records"), [{"n": 1}])
        self.assertIn("import job", logged)
        self.assertEqual(str(state.get("cursor")), "2026-01-02")

    # @feature data-store.import-script-sandbox
    def test_a_job_script_cannot_write_to_the_site_or_act_beyond_its_table(self):
        todo = self.todo.name
        target = os.path.join(tempfile.gettempdir(), "insights_import_job_file_test")
        self.addCleanup(lambda: os.path.exists(target) and os.remove(target))
        acts = {
            "set_value": f"frappe.db.set_value('ToDo', '{todo}', 'description', 'x')",
            "save": f"frappe.get_doc('ToDo', '{todo}').save()",
            "delete_doc": f"frappe.delete_doc('ToDo', '{todo}')",
            "enqueue": "frappe.enqueue('frappe.client.get_count', doctype='User')",
            "call": "frappe.call('frappe.client.get_count', doctype='User')",
            "sendmail": "frappe.sendmail(recipients=['a@example.com'], subject='s', message='m')",
            "write sql": f"frappe.db.sql(\"update tabToDo set description='x' where name='{todo}'\")",
            "after_commit": "frappe.db.after_commit.add(len)",
            "commit": "frappe.db.commit()",
            "rollback": "frappe.db.rollback()",
            "commit sql": "frappe.db.sql('commit')",
            "file": f"pandas.DataFrame(client.fetch('/items')).to_csv({target!r})",
        }
        not_in_sandbox = (AttributeError, "module has no attribute")
        refusal = {
            "set_value": not_in_sandbox,
            "save": (frappe.PermissionError, "cannot call save on a document"),
            "delete_doc": not_in_sandbox,
            "enqueue": not_in_sandbox,
            "call": not_in_sandbox,
            "sendmail": not_in_sandbox,
            "write sql": (frappe.PermissionError, "Read-Only queries are allowed"),
            # the sandbox `frappe.db` has no `after_commit`
            "after_commit": (TypeError, "'NoneType' object is not callable"),
            "commit": not_in_sandbox,
            "rollback": not_in_sandbox,
            "commit sql": (frappe.PermissionError, "Read-Only queries are allowed"),
            "file": (frappe.PermissionError, "cannot reach a file or a connection through to_csv"),
        }
        for act, code in acts.items():
            with self.subTest(act=act):
                with self.assertRaisesRegex(*refusal[act]):
                    self.run_script(code)
        self.assertFalse(os.path.exists(target))

        self.assertEqual(frappe.db.get_value("ToDo", todo, "description"), "import job")
        self.assertNotIn(len, frappe.db.after_commit._functions)
