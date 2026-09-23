import os
import tempfile
from unittest.mock import patch

import frappe
from frappe.utils.password import delete_all_passwords_for

from insights.insights.doctype.insights_data_source_v3.ibis_utils import (
    IbisQueryBuilder,
    get_code_results,
)
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import as_user, create_user, delete_users

SCRIPT_READER = "script-cache-reader@test.com"


class TestScriptQueryLogs(InsightsIntegrationTestCase):
    def run_code(self, code):
        published = []
        with patch(
            "frappe.publish_realtime",
            side_effect=lambda **kwargs: published.append(kwargs),
        ):
            try:
                results = get_code_results(code, variables={"token": "secret"})
            except Exception as e:
                return published, e
            return published, results

    def get_logs(self, published):
        events = [p for p in published if p.get("event") == "insights_script_log"]
        self.assertEqual(len(events), 1)
        return events[0]["message"]["logs"]

    # @feature query.script-logs
    def test_error_is_logged_with_line_number(self):
        code = "\n".join(
            [
                "rows = [{'a': 1}]",
                "results = rows[5]",
            ]
        )
        published, error = self.run_code(code)

        self.assertIsInstance(error, IndexError)
        logs = self.get_logs(published)
        self.assertIn("Line 2: results = rows[5]", logs[-1])
        self.assertIn("IndexError", logs[-1])

    # @feature query.script-logs
    def test_syntax_error_is_logged(self):
        published, error = self.run_code("results = [")

        self.assertIsInstance(error, SyntaxError)
        logs = self.get_logs(published)
        self.assertIn("SyntaxError", logs[-1])

    # @feature query.script-logs
    def test_prints_before_the_error_survive(self):
        code = "\n".join(
            [
                "print('step one')",
                "raise ValueError('boom')",
            ]
        )
        published, error = self.run_code(code)

        self.assertIsInstance(error, ValueError)
        logs = self.get_logs(published)
        self.assertEqual(logs[0], "step one")
        self.assertIn("ValueError: boom", logs[-1])

    # @feature query.script-logs
    def test_logs_are_published_on_success(self):
        code = "\n".join(
            [
                "print('done')",
                "results = [{'a': 1}]",
            ]
        )
        published, results = self.run_code(code)

        self.assertEqual(len(results), 1)
        logs = self.get_logs(published)
        self.assertEqual(logs[0], "done")
        self.assertRegex(logs[-1], r"^1 rows in [\d.]+s$")

    # @feature query.script-logs
    def test_a_run_for_someone_else_publishes_no_logs(self):
        """`IbisQueryBuilder.apply_code` runs a script under `runs_as` for a
        run-as-owner chart and under `permission_user` for an alert tick. What
        it prints was read as that user, and the realtime room is the caller's,
        so a reader of the chart gets nothing. The author running their own
        query still gets their logs."""
        from insights.permission_user import permission_user

        create_user(SCRIPT_READER, roles="Insights User")
        self.addCleanup(delete_users, SCRIPT_READER)
        code = "print(frappe.session.user)\nresults = [{'a': 1}]"

        with as_user(SCRIPT_READER), permission_user("Administrator"):
            published, _results = self.run_code(code)
        self.assertEqual(published, [])

        with as_user(SCRIPT_READER), permission_user(SCRIPT_READER):
            published, _results = self.run_code(code)
        self.assertEqual(self.get_logs(published)[0], SCRIPT_READER)

    # @feature query.script
    def test_empty_results_give_an_empty_table(self):
        published, results = self.run_code("results = []")

        self.assertEqual(list(results.columns), ["results"])
        self.assertEqual(len(results), 0)
        self.assertRegex(self.get_logs(published)[-1], r"^0 rows in [\d.]+s$")

    # @feature query.script-variables
    def test_variables_reach_the_script(self):
        _published, results = self.run_code("results = [{'a': token}]")

        self.assertEqual(results["a"].tolist(), ["secret"])

    # @feature query.script-variables
    def test_a_variable_with_no_value_names_itself(self):
        """`IbisQueryBuilder.apply_code`, on every run of a script query and of a
        chart over it. A copy made by `copy_cross_workbook_query_sources`
        carries a variable's name and never its secret; a stored value still
        reaches the script."""
        from insights.tests.factories import create_test_workbook

        workbook = create_test_workbook("Administrator")
        query = frappe.get_doc(
            {
                "doctype": "Insights Query v3",
                "title": "Script With A Secret",
                "workbook": workbook.name,
                "is_script_query": 1,
                "operations": [{"type": "code", "code": "results = [{'a': token}]"}],
                "variables": [
                    {"variable_name": "token", "variable_value": "secret"},
                    {"variable_name": "api_key"},
                ],
            }
        )
        query.flags.ignore_mandatory = True
        query.insert(ignore_permissions=True)
        query.reload()
        self.addCleanup(frappe.delete_doc, "Insights Workbook", workbook.name, force=True)

        with self.assertRaisesRegex(frappe.ValidationError, "api_key"):
            IbisQueryBuilder(query).build()

        query.variables = query.variables[:1]
        query.save(ignore_permissions=True)
        self.assertEqual(IbisQueryBuilder(query).build().execute()["a"].tolist(), ["secret"])


class TestScriptSandbox(InsightsIntegrationTestCase):
    """What `get_code_results` hands a script, on every run of a script query:
    the builder, a chart over it, a run-as-owner chart and an alert tick."""

    def before_test(self):
        from insights.tests.factories import create_test_workbook

        self.workbook = create_test_workbook("Administrator").name
        self.addCleanup(frappe.delete_doc, "Insights Workbook", self.workbook, force=True)

    def script_query(self, title, code, variables=None):
        return frappe.get_doc(
            {
                "doctype": "Insights Query v3",
                "title": title,
                "workbook": self.workbook,
                "is_script_query": 1,
                "operations": [{"type": "code", "code": code}],
                "variables": variables or [],
            }
        ).insert(ignore_permissions=True)

    # @feature query.script-sandbox
    def test_a_script_reads_frappe_data_and_calls_out(self):
        """The shapes the shipped scripts on insights.frappe.io use: a secret read
        off a document, another query's rows, a site table and an outbound POST."""
        inner = self.script_query("Sandbox Inner", "results = [{'a': 7}]")
        secret = self.script_query(
            "Sandbox Secret",
            "results = []",
            variables=[{"variable_name": "token", "variable_value": "s3cret"}],
        ).variables[0]
        code = "\n".join(
            [
                f"token = frappe.get_doc('Insights Query Variable', '{secret.name}').get_password('variable_value')",
                f"inner = frappe.get_doc('Insights Query v3', '{inner.name}').execute(force=True)['rows']",
                f"built = frappe.get_doc('Insights Query v3', '{inner.name}').build().columns",
                "users = frappe.db.sql('select count(*) from tabUser')[0][0]",
                "posted = frappe.make_post_request('https://logs.example.com/search', json={'q': 1})",
                "day = str(frappe.utils.getdate('2026-01-02'))",
                "results = [{'token': token, 'inner': inner[0]['a'], 'built': ','.join(built), 'users': users > 0, 'posted': posted['ok'], 'day': day}]",
            ]
        )

        # the network: frappe resolves the host before it sends
        with (
            patch("frappe.utils.safe_exec.validate_request_url"),
            patch("frappe.integrations.utils.make_request", return_value={"ok": 1}) as request,
        ):
            results = get_code_results(code)

        self.assertEqual(
            results.to_dict(orient="records"),
            [{"token": "s3cret", "inner": 7, "built": "a", "users": True, "posted": 1, "day": "2026-01-02"}],
        )
        self.assertEqual(request.call_args.args[:2], ("POST", "https://logs.example.com/search"))

    # @feature query.script-sandbox
    def test_a_script_run_for_someone_else_reads_their_user_and_nothing_of_the_callers_session(self):
        """`script_session` swaps the user, not the session data, and a run-as-owner
        chart caches the script's rows for every reader it serves. The caller's
        own run reads the same one key."""
        from insights.permission_user import permission_user

        create_user(SCRIPT_READER, roles="Insights User")
        self.addCleanup(delete_users, SCRIPT_READER)
        frappe.local.session.data.csrf_token = "caller-token"
        self.addCleanup(frappe.local.session.data.pop, "csrf_token")
        code = (
            "results = [{'keys': ','.join(sorted(frappe.session)), 'user': frappe.session.user,"
            " 'full_name': 'full_name' in frappe}]"
        )

        for runs_for in (SCRIPT_READER, "Administrator"):
            with self.subTest(runs_for=runs_for), permission_user(runs_for):
                rows = get_code_results(code).to_dict(orient="records")
                self.assertEqual(rows, [{"keys": "user", "user": runs_for, "full_name": False}])

    # @feature query.script-sandbox query.expression-cannot-reach-files
    def test_a_script_reaches_no_file(self):
        """A frame's writers take a path, and one built from another frame, an
        array or a table built by a query is as reachable as the one the script
        made. The frame itself and its values still come back."""
        target = os.path.join(tempfile.gettempdir(), "insights_script_file_test")
        self.addCleanup(lambda: os.path.exists(target) and os.remove(target))
        private_file = frappe.get_site_path("private", "files", "insights-script-probe.pdf")
        with open(private_file, "wb") as f:
            f.write(b"%PDF-1.4")
        self.addCleanup(os.remove, private_file)
        frame = "pandas.DataFrame([{'a': 1}])"
        acts = {
            "read_csv": f"pandas.read_csv({target!r})",
            "to_pickle": f"{frame}.to_pickle({target!r})",
            "to_parquet": f"{frame}.head().to_parquet({target!r})",
            "to_excel": f"{frame}.to_excel({target!r})",
            "to_csv": f"{frame}['a'].to_csv({target!r})",
            "class to_csv": f"pandas.DataFrame.to_csv({frame}, {target!r})",
            "tofile": f"{frame}.values.tofile({target!r})",
            "table to_csv": f"frappe.get_doc('Insights Query v3', '{self.script_query('Files Inner', 'results = [{\'a\': 1}]').name}').build().to_csv({target!r})",
            "a private file": "frappe.utils.pdf_to_base64('/private/files/insights-script-probe.pdf')",
        }
        for act, code in acts.items():
            with self.subTest(act=act):
                with self.assertRaises((AttributeError, frappe.PermissionError)):
                    get_code_results(f"{code}\nresults = []")
                self.assertFalse(os.path.exists(target))

        rows = get_code_results(f"results = pandas.DataFrame.from_records({frame}.to_dict(orient='records'))")
        self.assertEqual(rows.to_dict(orient="records"), [{"a": 1}])

    # @feature query.script-sandbox
    def test_a_script_reaches_no_connection(self):
        """A query a script reads builds a relation on the data source's connection,
        where `raw_sql` runs any statement and commits it outside the script's
        savepoint. Its rows and a select through `sql` stay a script's to read."""
        todo = frappe.get_doc({"doctype": "ToDo", "description": "connection"}).insert(
            ignore_permissions=True
        )
        self.addCleanup(frappe.delete_doc, "ToDo", todo.name, force=True)
        query = frappe.get_doc(
            {
                "doctype": "Insights Query v3",
                "title": "Sandbox Site Table",
                "workbook": self.workbook,
                "use_live_connection": 1,
                "operations": [
                    {
                        "type": "source",
                        "table": {"type": "table", "data_source": "Site DB", "table_name": "tabToDo"},
                    }
                ],
            }
        ).insert()
        table = f"frappe.get_doc('Insights Query v3', '{query.name}').build()"
        acts = {
            # for an admin the relation is the permlevel projection over the table
            "op": f"{table}.op().parent.source.raw_sql(\"update tabToDo set description='x' where name='{todo.name}'\")",
            "get_backend": f"{table}.get_backend()",
            "cache": f"{table}.cache()",
            "release": f"{table}.release()",
            "visualize": f"{table}.visualize()",
        }
        for act, code in acts.items():
            for lines in (f"{code}\nresults = []", f"t = {table}\n{code.replace(table, 't')}\nresults = []"):
                with self.subTest(act=act, lines=lines.count("\n") + 1):
                    with self.assertRaises(frappe.PermissionError):
                        get_code_results(lines)

        # the connection reads committed rows only, so these ask for the shape
        rows = get_code_results(
            f"rows = {table}.select('name').limit(1).execute()\n"
            f"counted = {table}.sql('select count(*) as n from tabToDo').execute()\n"
            "results = [{'rows': ','.join(rows.columns), 'sql': ','.join(counted.columns)}]"
        )
        self.assertEqual(rows.to_dict(orient="records"), [{"rows": "name", "sql": "n"}])
        self.assertEqual(frappe.db.get_value("ToDo", todo.name, "description"), "connection")

    # @feature query.script-sandbox
    def test_a_script_cannot_act_beyond_a_read(self):
        """Run as the caller and as someone else, since a chart run as its
        owner swaps the session."""
        from insights.permission_user import permission_user

        todo = frappe.get_doc({"doctype": "ToDo", "description": "sandbox"}).insert(ignore_permissions=True)
        self.addCleanup(frappe.delete_doc, "ToDo", todo.name, force=True)
        create_user(SCRIPT_READER, roles="Insights User")
        self.addCleanup(delete_users, SCRIPT_READER)
        self.addCleanup(frappe.db.delete, "UTM Source", {"name": "insights-script-probe"})

        acts = {
            "enqueue": "frappe.enqueue('frappe.client.get_count', doctype='User')",
            "call": "frappe.call('frappe.client.get_count', doctype='User')",
            "sendmail": "frappe.sendmail(recipients=['a@example.com'], subject='s', message='m')",
            "set_value": f"frappe.db.set_value('ToDo', '{todo.name}', 'description', 'x')",
            "save": f"frappe.get_doc('ToDo', '{todo.name}').save()",
            "insert": "frappe.get_doc({'doctype': 'ToDo', 'description': 'x'}).insert()",
            "submit": f"frappe.get_doc('ToDo', '{todo.name}').submit()",
            "delete": f"frappe.get_doc('ToDo', '{todo.name}').delete()",
            "db_set": f"frappe.get_doc('ToDo', '{todo.name}').db_set('description', 'x')",
            "cached save": f"frappe.get_cached_doc('ToDo', '{todo.name}').save()",
            "last save": "frappe.get_last_doc('ToDo').save()",
            "meta save": f"frappe.get_doc('ToDo', '{todo.name}').meta.save()",
            "delete_doc": f"frappe.delete_doc('ToDo', '{todo.name}')",
            "new_doc": "frappe.new_doc('ToDo')",
            "write sql": f"frappe.db.sql(\"update tabToDo set description='x' where name='{todo.name}'\")",
            "before_commit": "frappe.db.before_commit.add(len)",
            "after_commit": "frappe.db.after_commit.add(len)",
            "after_rollback": "frappe.db.after_rollback.add(len)",
            "commit": "frappe.db.commit()",
            "rollback": "frappe.db.rollback()",
            "commit sql": "frappe.db.sql('commit')",
            "run_script": "run_script('any')",
            "map_trackers": "frappe.utils.map_trackers({'utm_source': 'insights-script-probe'}, create=True)",
        }
        not_in_sandbox = (AttributeError, "module has no attribute")
        # a name `frappe.db` lacks reads as a no-op function
        no_hook = (TypeError, "'NoneType' object is not callable")
        refusal = {
            "enqueue": not_in_sandbox,
            "call": not_in_sandbox,
            "sendmail": not_in_sandbox,
            "set_value": not_in_sandbox,
            "delete_doc": not_in_sandbox,
            "new_doc": not_in_sandbox,
            "map_trackers": not_in_sandbox,
            "write sql": (frappe.PermissionError, "Read-Only queries are allowed"),
            "before_commit": no_hook,
            "after_commit": no_hook,
            "after_rollback": no_hook,
            "commit": not_in_sandbox,
            "rollback": not_in_sandbox,
            "commit sql": (frappe.PermissionError, "Read-Only queries are allowed"),
            "run_script": (NameError, "name 'run_script' is not defined"),
        }
        for act in ("save", "insert", "submit", "delete", "db_set", "cached save", "last save", "meta save"):
            method = act.rpartition(" ")[2]
            refusal[act] = (frappe.PermissionError, f"cannot call {method} on a document")

        for runs_for in ("Administrator", SCRIPT_READER):
            for act, code in acts.items():
                with self.subTest(act=act, runs_for=runs_for), permission_user(runs_for):
                    with self.assertRaisesRegex(*refusal[act]):
                        get_code_results(f"{code}\nresults = []")

        self.assertEqual(frappe.db.get_value("ToDo", todo.name, "description"), "sandbox")
        self.assertFalse(frappe.db.exists("UTM Source", "insights-script-probe"))
        for hooks in (frappe.db.before_commit, frappe.db.after_commit, frappe.db.after_rollback):
            self.assertNotIn(len, hooks._functions)


class TestScriptAuthor(InsightsIntegrationTestCase):
    """Who may put trusted code - a script, an expression that runs SQL or a
    stored procedure call - on a query, a chart or an alert, whichever door
    brings it."""

    def before_test(self):
        from insights.tests.factories import create_test_workbook

        create_user(SCRIPT_READER, roles="Insights User")
        self.addCleanup(delete_users, SCRIPT_READER)
        self.workbook = create_test_workbook(SCRIPT_READER).name
        self.addCleanup(self.delete_workbooks)

    def delete_workbooks(self):
        for workbook in frappe.get_all("Insights Workbook", {"owner": SCRIPT_READER}, pluck="name"):
            frappe.delete_doc("Insights Workbook", workbook, force=True, delete_permanently=True)

    def script_query(self, title, code="results = [{'a': 1}]", operations=None):
        return frappe.get_doc(
            {
                "doctype": "Insights Query v3",
                "title": title,
                "workbook": self.workbook,
                "is_script_query": 1,
                "operations": operations or [{"type": "code", "code": code}],
            }
        )

    # @feature query.script-author
    def test_only_an_admin_adds_or_changes_a_script(self):
        """`frappe.client.insert` and `frappe.client.set_value`, the builder's
        save, and `insights.api.run_doc_method`, the builder's run of the query
        on screen. An editor of the workbook keeps running and saving the script
        an admin wrote."""
        from frappe.client import insert, set_value

        from insights.api import run_doc_method
        from insights.tests.test_run_as_owner import as_http_request

        with as_user(SCRIPT_READER), self.assertRaisesRegex(frappe.PermissionError, "Editor Script"):
            insert(self.script_query("Editor Script").as_dict())

        stored = self.script_query("Admin Script").insert()
        with as_user(SCRIPT_READER), as_http_request():
            set_value("Insights Query v3", stored.name, "title", "Admin Script Renamed")
            ran = run_doc_method("execute", stored.as_dict(), {"force": True})
            self.assertEqual(ran["rows"], [{"a": 1}])

            edited = [{"type": "code", "code": "results = [{'a': 2}]"}]
            with self.assertRaisesRegex(frappe.PermissionError, "Admin Script Renamed"):
                set_value("Insights Query v3", stored.name, "operations", frappe.as_json(edited))
            unsaved = {
                **stored.as_dict(),
                "title": "Admin Script Renamed",
                "operations": frappe.as_json(edited),
            }
            with self.assertRaisesRegex(frappe.PermissionError, "Admin Script Renamed"):
                run_doc_method("execute", unsaved, {"force": True})

        stored.reload()
        self.assertEqual(frappe.parse_json(stored.operations)[0]["code"], "results = [{'a': 1}]")

    # @feature query.script-author
    def test_only_an_admin_adds_or_changes_a_sql_query_that_runs_a_stored_procedure(self):
        """`IbisQueryBuilder.apply_sql` runs a statement that starts with `exec`
        as written on a source with stored procedures on, so it binds no table
        to the reader's permissions. Through `frappe.client.insert` and
        `set_value`, the builder's run of the query on screen (`run_doc_method`)
        and `InsightsQueryv3.duplicate`, in any case, after whitespace or a
        comment. An editor keeps running the one an admin wrote, and writes a
        SELECT."""
        from frappe.client import insert, set_value

        from insights.api import run_doc_method
        from insights.tests.test_run_as_owner import as_http_request

        frappe.db.set_value("Insights Data Source v3", "Site DB", "enable_stored_procedure_execution", 1)
        self.addCleanup(
            frappe.db.set_value, "Insights Data Source v3", "Site DB", "enable_stored_procedure_execution", 0
        )

        def native_query(title, raw_sql):
            return frappe.get_doc(
                {
                    "doctype": "Insights Query v3",
                    "title": title,
                    "workbook": self.workbook,
                    "is_native_query": 1,
                    "use_live_connection": 1,
                    "operations": [{"type": "sql", "data_source": "Site DB", "raw_sql": raw_sql}],
                }
            )

        procedure = "EXECUTE IMMEDIATE 'SELECT 1 AS a'"
        spellings = (
            procedure,
            "exec sp_who",
            "EXEC sp_who",
            f"  \n {procedure}",
            f"/* a note */ {procedure}",
            f"-- a note\n{procedure}",
        )
        with as_user(SCRIPT_READER):
            for index, raw_sql in enumerate(spellings):
                title = f"Editor Procedure {index}"
                with self.subTest(raw_sql=raw_sql), self.assertRaisesRegex(frappe.PermissionError, title):
                    insert(native_query(title, raw_sql).as_dict())
            plain = insert(native_query("Editor Select", "SELECT 1 AS a").as_dict())
            self.assertTrue(plain["name"])

        stored = native_query("Admin Procedure", procedure).insert()
        with as_user(SCRIPT_READER), as_http_request():
            ran = run_doc_method("execute", stored.as_dict(), {"force": True})
            self.assertEqual(ran["rows"], [{"a": 1}])

            edited = [
                {"type": "sql", "data_source": "Site DB", "raw_sql": "EXECUTE IMMEDIATE 'SELECT 2 AS a'"}
            ]
            with self.assertRaisesRegex(frappe.PermissionError, "Admin Procedure"):
                set_value("Insights Query v3", stored.name, "operations", frappe.as_json(edited))
            unsaved = {**stored.as_dict(), "operations": frappe.as_json(edited)}
            with self.assertRaisesRegex(frappe.PermissionError, "Admin Procedure"):
                run_doc_method("execute", unsaved, {"force": True})
            with self.assertRaisesRegex(frappe.PermissionError, "Admin Procedure"):
                frappe.get_doc("Insights Query v3", stored.name).duplicate()

    # @feature query.script-variables
    def test_a_script_reads_the_variables_its_stored_query_carries(self):
        """`insights.api.run_doc_method`, the builder's run of the query on
        screen, and a query that sources the script. The body's variable rows
        are the caller's: renamed to another query's row, or carrying a value
        of their own, the script still reads its own query's stored secret."""
        from insights.api import run_doc_method
        from insights.tests.test_run_as_owner import as_http_request

        def with_token(title, value):
            query = self.script_query(title, "results = [{'v': token}]")
            query.append("variables", {"variable_name": "token", "variable_value": value})
            return query.insert()

        stored = with_token("Admin Script Own Token", "OWN_SECRET")
        other = with_token("Admin Script Other Token", "OTHER_SECRET")
        sourcing = frappe.get_doc(
            {
                "doctype": "Insights Query v3",
                "title": "Query Over Admin Script",
                "workbook": self.workbook,
                "operations": [{"type": "source", "table": {"type": "query", "query_name": stored.name}}],
            }
        ).insert()

        body = stored.as_dict()
        renamed = {**body, "variables": [{**body["variables"][0], "name": other.variables[0].name}]}
        own_value = {**body, "variables": [{"variable_name": "token", "variable_value": "CALLERS"}]}
        with as_user(SCRIPT_READER), as_http_request():
            for sent in (renamed, own_value, sourcing.as_dict()):
                ran = run_doc_method("execute", sent, {"force": True})
                self.assertEqual(ran["rows"], [{"v": "OWN_SECRET"}])

    # @feature query.script-author
    def test_only_an_admin_adds_or_changes_an_expression_that_runs_sql(self):
        """`q.sql` reads any table on the connection past the reader's permissions,
        so an expression that calls it is trusted code wherever it sits: any
        operation, a chart's config, an alert's condition, one statement or
        several. Through `frappe.client.insert` and `set_value`, the builder's run
        of the query on screen (`run_doc_method`), and a chart's and an alert's
        save. An editor keeps running and saving what an admin wrote, and writes
        an expression that runs no SQL."""
        from frappe.client import insert, set_value

        from insights.api import run_doc_method
        from insights.tests.test_run_as_owner import as_http_request

        def sql_query(title, expression):
            return frappe.get_doc(
                {
                    "doctype": "Insights Query v3",
                    "title": title,
                    "workbook": self.workbook,
                    "use_live_connection": 1,
                    "operations": [
                        {
                            "type": "source",
                            "table": {"type": "table", "data_source": "Site DB", "table_name": "tabToDo"},
                        },
                        {
                            "type": "custom_operation",
                            "expression": {"type": "expression", "expression": expression},
                        },
                    ],
                }
            )

        one_line = "q.sql('select name, status from tabToDo')"
        several = "rows = q.sql('select name, status from tabToDo')\nrows"
        in_a_filter = {
            "type": "filter",
            "expression": {"type": "expression", "expression": "q.sql('select 1 as a').a.max() > 0"},
        }

        with as_user(SCRIPT_READER):
            for title, expression in (("Editor SQL", one_line), ("Editor SQL Lines", several)):
                with self.assertRaisesRegex(frappe.PermissionError, title):
                    insert(sql_query(title, expression).as_dict())
            plain = insert(sql_query("Editor Plain", "q.filter(q.status == 'Open')").as_dict())
            self.assertTrue(plain["name"])

        stored = sql_query("Admin SQL", one_line).insert()
        with as_user(SCRIPT_READER), as_http_request():
            set_value("Insights Query v3", stored.name, "title", "Admin SQL Renamed")
            ran = run_doc_method("execute", stored.as_dict(), {"force": True})
            self.assertIn("status", [column["name"] for column in ran["columns"]])

            edited = [*frappe.parse_json(stored.operations), in_a_filter]
            with self.assertRaisesRegex(frappe.PermissionError, "Admin SQL Renamed"):
                set_value("Insights Query v3", stored.name, "operations", frappe.as_json(edited))
            unsaved = {**stored.as_dict(), "title": "Admin SQL Renamed", "operations": frappe.as_json(edited)}
            with self.assertRaisesRegex(frappe.PermissionError, "Admin SQL Renamed"):
                run_doc_method("execute", unsaved, {"force": True})

            chart = {
                "doctype": "Insights Chart v3",
                "title": "Editor SQL Chart",
                "workbook": self.workbook,
                "query": stored.name,
                "chart_type": "Bar",
                "config": {"y_axis": {"series": [{"measure": {"measure_name": "m", **in_a_filter}}]}},
            }
            with self.assertRaisesRegex(frappe.PermissionError, "Editor SQL Chart"):
                frappe.get_doc(chart).insert(ignore_permissions=True)
            alert = {
                "doctype": "Insights Alert",
                "title": "Editor SQL Alert",
                "query": stored.name,
                "custom_condition": 1,
                "condition": "q.sql('select 1 as a').a.max() > 0",
                "disabled": 1,
            }
            with self.assertRaisesRegex(frappe.PermissionError, "Editor SQL Alert"):
                frappe.get_doc(alert).insert(ignore_permissions=True)

        stored.reload()
        self.assertEqual(len(frappe.parse_json(stored.operations)), 2)

    # @feature query.script-author
    def test_the_script_editor_is_offered_to_whoever_may_save_a_script(self):
        """`get_user_info` publishes `can_write_trusted_code`, which
        `ScriptQueryEditor` and `WorkbookQueryEmptyState` offer the editor from.
        It is the answer a save gives: a System Manager without the `Insights
        Admin` role writes a script, and a holder of the role outside the Admin
        team does not."""
        import frappe.share
        from frappe.client import insert

        from insights.api import get_user_info
        from insights.insights.doctype.insights_team.insights_team import clear_cache

        manager, role_holder = "script-manager@test.com", "script-role-holder@test.com"
        create_user(manager, roles=["Insights User", "System Manager"])
        create_user(role_holder, roles=["Insights User", "Insights Admin"])
        self.addCleanup(delete_users, manager, role_holder)
        frappe.db.delete("Insights Team Member", {"parent": "Admin", "user": role_holder})
        clear_cache()
        frappe.share.add_docshare(
            "Insights Workbook", self.workbook, manager, write=1, flags={"ignore_share_permission": True}
        )
        frappe.share.add_docshare(
            "Insights Workbook", self.workbook, role_holder, write=1, flags={"ignore_share_permission": True}
        )

        for user, offered in ((manager, True), (role_holder, False), (SCRIPT_READER, False)):
            with self.subTest(user=user), as_user(user):
                self.assertEqual(get_user_info()["can_write_trusted_code"], offered)
                if offered:
                    insert(self.script_query(f"Script by {user}").as_dict())
                else:
                    with self.assertRaises(frappe.PermissionError):
                        insert(self.script_query(f"Script by {user}").as_dict())

    def admin_sql_query(self, *after):
        return frappe.get_doc(
            {
                "doctype": "Insights Query v3",
                "title": "Admin SQL",
                "workbook": self.workbook,
                "use_live_connection": 1,
                "operations": [
                    {
                        "type": "source",
                        "table": {"type": "table", "data_source": "Site DB", "table_name": "tabToDo"},
                    },
                    {
                        "type": "custom_operation",
                        "expression": {
                            "type": "expression",
                            "expression": "q.sql('select name, status, priority from tabToDo')",
                        },
                    },
                    *after,
                ],
            }
        ).insert()

    # @feature query.script-author alerts.test-send
    def test_an_alert_sends_only_the_trusted_code_its_stored_alert_carries(self):
        """`AlertSetupDialog` and the desk form send an alert through
        `run_doc_method` with the condition on screen, saved or not; the tick
        sends the stored one. An editor sends an admin's stored condition, and
        their own that runs no SQL."""
        from insights.api import run_doc_method
        from insights.tests.test_run_as_owner import as_http_request

        query = self.admin_sql_query()
        admin_condition = "q.sql('select 1 as a').a.max() > 5"
        stored = frappe.get_doc(
            {
                "doctype": "Insights Alert",
                "title": "Admin SQL Alert",
                "query": query.name,
                "channel": "Email",
                "custom_condition": 1,
                "condition": admin_condition,
                "recipients": SCRIPT_READER,
                "message": "hello",
                "disabled": 1,
            }
        ).insert()
        self.addCleanup(frappe.delete_doc, "Insights Alert", stored.name, force=True)
        editor_condition = "q.sql('select 1 as a').a.max() > 6"

        def send(alert):
            with as_user(SCRIPT_READER), as_http_request(), patch("frappe.sendmail") as sendmail:
                run_doc_method("send_alert", alert)
            return sendmail.call_count

        unsaved = {**stored.as_dict(), "name": "new-alert-sql", "title": "Editor SQL Alert"}
        for alert in (
            {**unsaved, "condition": editor_condition},
            {**stored.as_dict(), "condition": editor_condition},
            # the admin's condition, carried to a document that does not store it
            {**unsaved, "condition": admin_condition},
        ):
            with self.subTest(name=alert["name"], condition=alert["condition"]):
                with self.assertRaisesRegex(frappe.PermissionError, alert["title"]):
                    send(alert)

        self.assertEqual(send(stored.as_dict()), 0)
        self.assertEqual(send({**unsaved, "condition": "status == 'Nothing'"}), 0)

    # @feature query.script-author charts.drill-breakdown-offers
    def test_a_builder_drill_runs_the_trusted_code_its_source_query_carries(self):
        """The query builder drills its result through
        `insights.api.authoring.get_drill_dimensions` with the operations on
        screen, which run as a throwaway preview named after no stored document.
        An editor drills an admin's stored `.sql`, and not one of their own."""
        from insights.api.authoring import get_drill_dimensions
        from insights.insights.doctype.insights_data_source_v3.insights_data_source_v3 import (
            db_connections,
        )
        from insights.tests.test_run_as_owner import as_http_request

        summarize = {
            "type": "summarize",
            "measures": [
                {
                    "measure_name": "Todos",
                    "column_name": "name",
                    "aggregation": "count",
                    "data_type": "Integer",
                }
            ],
            "dimensions": [{"dimension_name": "status", "column_name": "status", "data_type": "String"}],
        }
        query = self.admin_sql_query(summarize)
        operations = frappe.parse_json(query.operations)

        with as_user(SCRIPT_READER), as_http_request(), db_connections():
            dimensions = get_drill_dimensions(query=query.name, operations=operations)["dimensions"]
            self.assertIn("priority", [d["name"] for d in dimensions])

            edited = [
                *operations[:2],
                {
                    "type": "filter",
                    "expression": {"type": "expression", "expression": "q.sql('select 1 as a').a.max() > 0"},
                },
                summarize,
            ]
            with self.assertRaisesRegex(frappe.PermissionError, "runs SQL"):
                get_drill_dimensions(query=query.name, operations=edited)

    # @feature query.script-author query.duplicate query.copy-paste workbook.duplicate workbook.copy-paste
    def test_an_import_or_copy_that_brings_a_script_names_the_script_queries(self):
        """`InsightsQueryv3.duplicate`, `InsightsWorkbook.import_query` (paste),
        `InsightsWorkbook.duplicate` and `insights.api.workbooks.import_workbook`,
        each as an editor who wrote none of the scripts. An admin's import of
        the same file goes in."""
        from insights.api.workbooks import import_workbook

        source = self.script_query("Source Script").insert()
        consumer = self.script_query(
            "Consumer Script",
            operations=[
                {"type": "source", "table": {"type": "query", "query_name": source.name}},
                {"type": "code", "code": "results = []"},
            ],
        ).insert()
        workbook = frappe.get_doc("Insights Workbook", self.workbook)
        workbook_file = workbook.export()
        query_file = consumer.export()
        target = frappe.get_doc({"doctype": "Insights Workbook", "title": "Paste Target"})
        target.insert(ignore_permissions=True)
        frappe.db.set_value("Insights Workbook", target.name, "owner", SCRIPT_READER)

        with as_user(SCRIPT_READER):
            with self.assertRaisesRegex(frappe.PermissionError, "Source Script"):
                frappe.get_doc("Insights Query v3", source.name).duplicate()
            with self.assertRaisesRegex(frappe.PermissionError, "Consumer Script.*Source Script"):
                frappe.get_doc("Insights Workbook", target.name).import_query(query_file)
            for door in (workbook.duplicate, lambda: import_workbook(workbook_file)):
                with self.assertRaisesRegex(frappe.PermissionError, "Source Script.*Consumer Script"):
                    door()
        self.assertEqual(frappe.db.count("Insights Query v3", {"workbook": target.name}), 0)

        imported = import_workbook(workbook_file)["workbook"]
        self.addCleanup(frappe.delete_doc, "Insights Workbook", imported, force=True, delete_permanently=True)
        self.addCleanup(
            frappe.delete_doc, "Insights Workbook", target.name, force=True, delete_permanently=True
        )
        self.assertEqual(frappe.db.count("Insights Query v3", {"workbook": imported}), 2)


class TestScriptQueryCache(InsightsIntegrationTestCase):
    def build(self, code, force=False):
        doc = frappe._dict(
            name="Script Query Cache Test",
            title="Script Query Cache Test",
            use_live_connection=0,
            operations=frappe.as_json([{"type": "code", "code": code}]),
        )
        builder = IbisQueryBuilder(doc)
        builder.force = force
        return builder.build()

    # @feature query.script
    def test_empty_results_build_a_queryable_table(self):
        result = self.build("results = []").execute()

        self.assertEqual(list(result.columns), ["results"])
        self.assertEqual(len(result), 0)

    # @feature query.script-variables
    def test_a_variable_change_reruns_the_script(self):
        """`IbisQueryBuilder.apply_code`, on the run after the query editor saves
        a variable's new value."""
        from insights.tests.factories import create_test_workbook

        workbook = create_test_workbook("Administrator").name
        self.addCleanup(frappe.delete_doc, "Insights Workbook", workbook, force=True)
        query = frappe.get_doc(
            {
                "doctype": "Insights Query v3",
                "title": "Script Variable Changed",
                "workbook": workbook,
                "is_script_query": 1,
                "operations": [{"type": "code", "code": "results = [{'a': token}]"}],
                "variables": [{"variable_name": "token", "variable_value": "one"}],
            }
        ).insert()
        self.assertEqual(IbisQueryBuilder(query).build().execute()["a"].tolist(), ["one"])

        query.variables[0].variable_value = "two"
        query.save()
        self.assertEqual(IbisQueryBuilder(query).build().execute()["a"].tolist(), ["two"])

    # @feature query.script-force-run
    def test_force_skips_the_code_cache(self):
        # a run of its own, so an earlier run's cached results do not answer it
        run = frappe.generate_hash()
        code = f"import_count = frappe.db.count('DocType')\nresults = [{{'a': import_count, 'run': '{run}'}}]"

        with patch(
            "insights.insights.doctype.insights_data_source_v3.ibis_utils.get_code_results",
            wraps=get_code_results,
        ) as spy:
            self.build(code).execute()
            self.build(code).execute()
            self.assertEqual(spy.call_count, 1)

            self.build(code, force=True).execute()
            self.assertEqual(spy.call_count, 2)

    # @feature query.script
    def test_one_users_script_output_is_not_served_to_another(self):
        """`IbisQueryBuilder.apply_code` runs a script for every chart and alert
        on a script query. The script reads as the user it runs for, so its cached
        output is theirs: two readers of a chart that runs as its reader each
        run it for themselves. The query is stored, since only an admin runs a
        script nobody saved (Q17)."""
        from insights.tests.factories import create_test_workbook

        create_user(SCRIPT_READER, roles="Insights User")
        self.addCleanup(delete_users, SCRIPT_READER)
        workbook = create_test_workbook("Administrator").name
        self.addCleanup(frappe.delete_doc, "Insights Workbook", workbook, force=True)
        query = frappe.get_doc(
            {
                "doctype": "Insights Query v3",
                "title": "Script Read As Its Reader",
                "workbook": workbook,
                "is_script_query": 1,
                "operations": [{"type": "code", "code": "results = [{'user': frappe.session.user}]"}],
            }
        ).insert()

        def reads_as():
            return IbisQueryBuilder(query).build().execute()["user"].tolist()

        self.assertEqual(reads_as(), ["Administrator"])
        with as_user(SCRIPT_READER):
            self.assertEqual(reads_as(), [SCRIPT_READER])
        self.assertEqual(reads_as(), ["Administrator"])


class AVariableSecretGoesWithItsVariable(InsightsIntegrationTestCase):
    """frappe deletes the secrets of the document it deletes, never those of a
    child row, so a script query's variables would leave theirs in `__Auth`."""

    def before_test(self):
        from insights.tests.factories import create_test_workbook

        self.workbook = create_test_workbook("Administrator").name
        self.addCleanup(frappe.delete_doc, "Insights Workbook", self.workbook, force=True)

    def script_query(self, title):
        return frappe.get_doc(
            {
                "doctype": "Insights Query v3",
                "title": title,
                "workbook": self.workbook,
                "is_script_query": 1,
                "operations": [{"type": "code", "code": "results = [{'a': token}]"}],
                "variables": [{"variable_name": "token", "variable_value": "secret"}],
            }
        ).insert(ignore_permissions=True)

    def has_secret(self, variable) -> bool:
        return bool(frappe.db.exists("__Auth", {"doctype": variable.doctype, "name": variable.name}))

    # @feature query.script-variables
    def test_deleting_a_script_query_clears_its_variables_secrets(self):
        """`InsightsQueryv3.after_delete`, reached from the sidebar's delete and
        from a workbook's, which is also how each test here cleans up. The
        query beside it keeps its own."""
        query = self.script_query("Script Secret Deleted")
        other = self.script_query("Script Secret Kept")

        frappe.delete_doc("Insights Query v3", query.name, force=True)

        self.assertFalse(self.has_secret(query.variables[0]))
        self.assertTrue(self.has_secret(other.variables[0]))

    # @feature query.script-variables
    def test_removing_a_variable_clears_its_secret(self):
        """`InsightsQueryv3.on_update`, reached from the query editor's save of
        its variables. The variable left on the query keeps its own."""
        query = self.script_query("Script Secret Removed")
        query.append("variables", {"variable_name": "kept", "variable_value": "still"})
        query.save(ignore_permissions=True)
        removed, kept = query.variables

        query.variables = [kept]
        query.save(ignore_permissions=True)

        self.assertFalse(self.has_secret(removed))
        self.assertTrue(self.has_secret(kept))

    # @feature query.script-variables
    def test_a_migrate_clears_the_secrets_a_deleted_variable_left(self):
        """`insights.patches.delete_orphaned_variable_secrets`, run once by
        `bench migrate`. The variable still on a query keeps its value."""
        from frappe.utils.password import set_encrypted_password

        from insights.patches.delete_orphaned_variable_secrets import execute

        kept = self.script_query("Script Secret Survives").variables[0]
        set_encrypted_password("Insights Query Variable", "deleted-variable", "left", "variable_value")
        self.addCleanup(delete_all_passwords_for, "Insights Query Variable", "deleted-variable")

        execute()

        self.assertFalse(frappe.db.exists("__Auth", {"doctype": kept.doctype, "name": "deleted-variable"}))
        self.assertTrue(self.has_secret(kept))
