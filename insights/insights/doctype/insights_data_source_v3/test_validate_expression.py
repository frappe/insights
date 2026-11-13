# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import json
import unittest

import frappe
import ibis
from frappe.utils.safe_exec import is_safe_exec_enabled

from insights.insights.doctype.insights_data_source_v3.ibis import functions, utils
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import as_user, create_user, delete_users

COLUMN_OPTIONS = json.dumps([{"value": "amount", "description": "Integer"}])


class TestValidateExpression(unittest.TestCase):
    """Regression tests for the validate_expression whitelisted endpoint.

    The endpoint executes a user-supplied expression to type-check it. It must
    never run that expression with the builtin exec(): an empty __builtins__ is
    not a sandbox and can be escaped through the object graph to reach
    __import__, giving any authenticated user remote code execution.
    """

    def _validate(self, expression):
        return utils.validate_expression(expression, COLUMN_OPTIONS)

    # --- security: the sandbox-escape payloads must never execute ---

    # @feature query.expression-cannot-run-code
    def test_attribute_escape_payload_is_rejected_without_executing(self):
        # If this expression ever executed, the unique sentinel raised by it
        # would surface in the returned error message. It must not.
        sentinel = "PWNED_BY_VALIDATE_EXPRESSION"
        payload = (
            "g = [c for c in ().__class__.__base__.__subclasses__() "
            'if c.__name__ == "ModuleSpec"][0]\n'
            'bi = g.__init__.__globals__["__builtins__"]\n'
            f'raise bi["Exception"]("{sentinel}:" + bi["__import__"]("os").sep)\n'
        )
        result = self._validate(payload)
        self.assertFalse(result["is_valid"])
        self.assertNotIn(sentinel, json.dumps(result))

    # @feature query.expression-cannot-run-code
    def test_name_call_escape_payload_is_rejected(self):
        # Variant routed through an assigned name instead of subscripts.
        sentinel = "PWNED_VIA_NAME_CALL"
        payload = (
            "g = [c for c in ().__class__.__base__.__subclasses__() "
            'if c.__name__ == "ModuleSpec"][0]\n'
            'imp = g.__init__.__globals__["__builtins__"]["__import__"]\n'
            f'raise imp("builtins").Exception("{sentinel}")\n'
        )
        result = self._validate(payload)
        self.assertFalse(result["is_valid"])
        self.assertNotIn(sentinel, json.dumps(result))

    # @feature query.expression-cannot-run-code
    def test_bare_dunder_access_is_rejected(self):
        result = self._validate("amount.__class__.__base__")
        self.assertFalse(result["is_valid"])

    # --- functionality: legit validation behaviour is preserved ---

    # @feature query.expression-validation
    def test_unknown_column_reports_friendly_error(self):
        result = self._validate("foo + 1")
        self.assertFalse(result["is_valid"])
        self.assertIn("foo", result["errors"][0]["message"])

    # @feature query.expression-validation
    def test_syntax_error_is_reported(self):
        result = self._validate("amount +")
        self.assertFalse(result["is_valid"])
        self.assertIn("Syntax error", result["errors"][0]["message"])

    # @feature query.expression-validation
    def test_empty_expression_is_valid(self):
        self.assertTrue(self._validate("   ")["is_valid"])

    # @feature query.expression-validation
    @unittest.skipUnless(is_safe_exec_enabled(), "expression execution requires server scripts enabled")
    # @feature query.expression-validation
    def test_valid_expression_passes(self):
        result = self._validate("amount.sum()")
        self.assertTrue(result["is_valid"], result)

    @unittest.skipUnless(is_safe_exec_enabled(), "expression execution requires server scripts enabled")
    # @feature query.expression-column-named-like-io
    def test_the_editor_reads_a_column_named_like_an_io_method_as_the_run_does(self):
        columns = json.dumps([{"value": "to_date", "description": "String"}])

        self.assertTrue(utils.validate_expression("q.to_date", columns)["is_valid"])
        with self.assertRaises(frappe.PermissionError):
            utils.validate_expression("q.to_csv('/tmp/does-not-matter.csv')", columns)

    @unittest.skipUnless(is_safe_exec_enabled(), "expression execution requires server scripts enabled")
    # @feature query.expression-validation
    def test_the_editor_refuses_a_missing_column_read_as_an_attribute(self):
        """A missing attribute once read as `None`, so `q.nope` was valid."""
        for expression in ("q.nope", "q.nope > 1"):
            with self.subTest(expression=expression):
                result = self._validate(expression)
                self.assertFalse(result["is_valid"])
                self.assertEqual(result["errors"][0]["message"], "Column 'nope' not found.")

    # --- the help the editor prints beside an expression ---

    # @feature query.expression-help
    def test_the_editor_lists_every_whitelisted_function(self):
        function_list = utils.get_function_list()

        self.assertIn("sum", function_list)
        self.assertIn("count", function_list)
        self.assertIn("if_else", function_list)
        self.assertIn("distinct_count", function_list)
        self.assertIn("selectors", function_list)

        self.assertEqual([name for name in function_list if name.startswith("_")], [])
        self.assertEqual(len(function_list), len(set(function_list)))

        for module_name in ("frappe", "ir", "math", "pd"):
            self.assertNotIn(module_name, function_list)

        # `ibis` is available as a namespace of vetted attributes, not as the module
        ibis_namespace = utils.get_functions()["ibis"]
        self.assertIn("literal", ibis_namespace)
        for refused in (
            "read_csv",
            "read_parquet",
            "connect",
            "get_backend",
            "table",
            "memtable",
            "parse_sql",
            "selectors",
        ):
            self.assertNotIn(refused, ibis_namespace)

    # @feature query.expression-help
    def test_completions_describe_the_function_being_written_and_the_columns_types(self):
        columns = json.dumps([{"value": "amount", "data_type": "Integer"}])

        answer = utils.get_code_completions("sum(|)", columns)

        self.assertEqual(answer["column_types"], {"amount": "Integer"})
        self.assertEqual(answer["current_function"]["name"], "sum")
        self.assertEqual(answer["current_function"]["current_param"], "column")


VALIDATOR = "expression-validator@test.com"


class TestValidateExpressionSandbox(InsightsIntegrationTestCase):
    """`validate_expression` is whitelisted for any signed-in user, and the
    expression editor calls it on every keystroke. The caller sends the column
    list. A column with no type passes the check but is never bound during
    evaluation, so the name `frappe` resolves to the sandbox's own `frappe`."""

    columns = json.dumps([{"value": "amount", "description": "Integer"}, {"value": "frappe"}])

    def before_test(self):
        create_user(VALIDATOR, roles="Insights User")
        self.addCleanup(delete_users, VALIDATOR)
        self.todo = frappe.get_doc({"doctype": "ToDo", "description": "validate"}).insert(
            ignore_permissions=True
        )
        self.addCleanup(frappe.delete_doc, "ToDo", self.todo.name, force=True)

    # @feature query.expression-cannot-run-code
    def test_validating_an_expression_writes_nothing_and_reads_only_what_the_caller_may(self):
        todo = self.todo.name
        acts = {
            "set_value": f"frappe.db.set_value('ToDo', '{todo}', 'description', 'x')",
            "save": f"doc = frappe.get_doc('ToDo', '{todo}')\ndoc.description = 'x'\ndoc.save()",
            "insert": "frappe.get_doc({'doctype': 'ToDo', 'description': 'x'}).insert()",
            "delete_doc": f"frappe.delete_doc('ToDo', '{todo}')",
            "enqueue": "frappe.enqueue('frappe.client.get_count', doctype='User')",
            "sendmail": "frappe.sendmail(recipients=['a@example.com'], subject='s', message='m')",
            "sql": f"frappe.db.sql(\"update tabToDo set description='x' where name='{todo}'\")",
            "after_commit": "frappe.db.after_commit.add(if_else)",
            "commit": "frappe.db.commit()",
            "rollback": "frappe.db.rollback()",
            # another user's ToDo: an Insights User reads only their own
            "read": f"frappe.get_doc('ToDo', '{todo}').description",
        }
        for runs_as in (VALIDATOR, "Administrator"):
            with as_user(runs_as):
                for act, code in acts.items():
                    if runs_as == "Administrator" and act == "read":
                        continue
                    with self.subTest(act=act, runs_as=runs_as):
                        result = utils.validate_expression(f"{code}\namount", self.columns)
                        self.assertFalse(result["is_valid"], result)

        self.assertEqual(frappe.db.get_value("ToDo", todo, "description"), "validate")
        self.assertNotIn(functions.if_else, frappe.db.after_commit._functions)
        self.assertTrue(utils.validate_expression("amount.sum()", self.columns)["is_valid"])


TODO_SOURCE = {
    "type": "source",
    "table": {"type": "table", "data_source": "Site DB", "table_name": "tabToDo"},
}


def mutate(new_name, expression, data_type="Auto"):
    return {
        "type": "mutate",
        "new_name": new_name,
        "data_type": data_type,
        "expression": {"type": "expression", "expression": expression},
    }


def rename(column_name, new_name):
    return {"type": "rename", "column": {"type": "column", "column_name": column_name}, "new_name": new_name}


def join_on(expression):
    return {
        "type": "join",
        "join_type": "left",
        "table": {"type": "table", "data_source": "Site DB", "table_name": "tabUser"},
        "select_columns": [{"type": "column", "column_name": "full_name"}],
        "join_condition": {"join_expression": {"type": "expression", "expression": expression}},
    }


def custom_operation(expression):
    return {"type": "custom_operation", "expression": {"type": "expression", "expression": expression}}


class TestEvaluateExpression(InsightsIntegrationTestCase):
    """What a run does with an expression, as `IbisQueryBuilder` evaluates it."""

    def build(self, *operations):
        from insights.insights.doctype.insights_data_source_v3.ibis_utils import IbisQueryBuilder
        from insights.insights.doctype.insights_data_source_v3.insights_data_source_v3 import db_connections

        query = frappe._dict(
            name="Evaluate Expression Test",
            title="Evaluate Expression Test",
            use_live_connection=1,
            operations=frappe.as_json([TODO_SOURCE, *operations]),
        )
        with db_connections():
            return IbisQueryBuilder(query).build()

    def assert_refused(self, exception, operations, *parts):
        frappe.clear_messages()
        with self.assertRaises(exception) as refusal:
            self.build(*operations)
        # the message log is what the UI and frappectl show; a bare SyntaxError left it empty
        shown = frappe.parse_json(frappe.local.message_log[-1])["message"]
        for part in parts:
            self.assertIn(part, str(refusal.exception))
            self.assertIn(part, shown)

    # @feature query.expression-error-names-operation
    def test_an_unknown_name_names_the_mutate_and_its_column(self):
        from insights.exceptions import UnknownColumn

        self.assert_refused(
            UnknownColumn,
            [mutate("doubled", "foo * 2")],
            "Operation 2 (mutate 'doubled'): UnknownColumn: NameError: name 'foo' is not defined. Expression: foo * 2",
        )

    # @feature query.expression-error-names-operation
    def test_a_syntax_error_names_the_filter_and_the_position(self):
        from insights.exceptions import ExpressionSyntaxError

        self.assert_refused(
            ExpressionSyntaxError,
            [{"type": "filter", "expression": {"type": "expression", "expression": "status =="}}],
            "Operation 2 (filter): ExpressionSyntaxError: SyntaxError: invalid syntax at line 1, column",
            "Expression: status ==",
        )

    # @feature query.expression-error-names-operation
    def test_a_type_error_names_the_measure(self):
        from insights.exceptions import ExpressionSyntaxError

        summarize = {
            "type": "summarize",
            "dimensions": [],
            "measures": [
                {
                    "measure_name": "total_length",
                    "data_type": "Integer",
                    "expression": {"type": "expression", "expression": "status.no_such_method()"},
                }
            ],
        }
        self.assert_refused(
            ExpressionSyntaxError,
            [summarize],
            "Operation 2 (summarize): ExpressionSyntaxError: Measure 'total_length': AttributeError:",
            "no_such_method",
            "Expression: status.no_such_method()",
        )

    # @feature query.expression-error-names-operation
    def test_an_ibis_error_outside_ibis_error_is_wrapped(self):
        """ibis's `SignatureValidationError` is not an `IbisError`, so a list of
        the classes to wrap once let it out bare."""
        from insights.exceptions import ExpressionSyntaxError

        self.assert_refused(
            ExpressionSyntaxError,
            [mutate("gap", "date - status")],
            "Operation 2 (mutate 'gap'): ExpressionSyntaxError: SignatureValidationError: `other`: StringColumn is not coercible",
            "Expression: date - status",
        )
        # its own text prints the expression tree of each argument
        self.assertNotIn("DatabaseTable", frappe.parse_json(frappe.local.message_log[-1])["message"])

    # @feature query.expression-error-names-operation
    def test_a_join_condition_names_the_join_and_the_expression(self):
        from insights.exceptions import UnknownColumn

        for expression in ("t1.allocated_to == t2.nope", "on = t1.allocated_to == t2.nope\non"):
            with self.subTest(expression=expression):
                self.assert_refused(
                    UnknownColumn,
                    [join_on(expression)],
                    "Operation 2 (join): UnknownColumn: AttributeError: 'Table' object has no attribute 'nope'",
                    f"Expression: {expression}",
                )

    # @feature query.expression-error-names-operation
    def test_a_custom_operation_names_the_operation_and_the_expression(self):
        from insights.exceptions import UnknownColumn

        self.assert_refused(
            UnknownColumn,
            [custom_operation("q.filter(q.nope == 'Open')")],
            "Operation 2 (custom_operation): UnknownColumn: AttributeError: 'Table' object has no attribute 'nope'",
            "Expression: q.filter(q.nope == 'Open')",
        )

    # @feature query.expression-error-names-operation
    def test_an_alert_condition_names_the_cause_and_the_expression(self):
        from insights.exceptions import UnknownColumn
        from insights.insights.doctype.insights_data_source_v3.insights_data_source_v3 import db_connections

        query = frappe.get_doc(
            {
                "doctype": "Insights Query v3",
                "title": "Evaluate Expression Test",
                "use_live_connection": 1,
                "operations": frappe.as_json([TODO_SOURCE]),
            }
        )
        frappe.clear_messages()
        with db_connections(), self.assertRaises(UnknownColumn):
            query.evaluate_alert_expression("state == 'Open'")
        self.assertEqual(
            [frappe.parse_json(m)["message"] for m in frappe.local.message_log],
            ["NameError: name 'state' is not defined. Expression: state == 'Open'"],
        )

    # @feature query.expression-error-names-operation
    def test_an_expression_of_only_a_comment_is_empty_and_says_so(self):
        from insights.exceptions import ExpressionSyntaxError

        self.assert_refused(
            ExpressionSyntaxError,
            [{"type": "filter", "expression": {"type": "expression", "expression": "# note"}}],
            "Operation 2 (filter): ExpressionSyntaxError: the expression is empty. Expression: # note",
        )

    # @feature query.expression-error-names-operation
    def test_a_column_named_with_an_underscore_is_refused_with_the_way_to_read_it(self):
        from insights.exceptions import ExpressionSyntaxError

        self.assert_refused(
            ExpressionSyntaxError,
            [mutate("assigned", "_assign + 'x'")],
            "Operation 2 (mutate 'assigned'): ExpressionSyntaxError: SyntaxError: Line 1: \"_assign\" is an invalid variable name",
            "Read the column as q['_assign']. Expression: _assign + 'x'",
        )
        self.assertNotIn("line None", frappe.parse_json(frappe.local.message_log[-1])["message"])

    # @feature query.expression-error-names-operation
    def test_a_misspelled_function_is_not_an_unknown_column(self):
        from insights.exceptions import ExpressionSyntaxError

        self.assert_refused(
            ExpressionSyntaxError,
            [mutate("total", "sumx(status)")],
            "NameError: name 'sumx' is not defined",
        )

    # @feature query.expression-error-names-operation
    def test_a_functions_own_refusal_keeps_its_class_and_names_the_operation(self):
        self.assert_refused(
            frappe.ValidationError,
            [mutate("amount", "json_value(description, 'amount', 'money')")],
            "Operation 2 (mutate 'amount'): ValidationError: Invalid type 'money' for json_value",
        )
        with self.assertRaises(frappe.ValidationError) as refusal:
            self.build(mutate("amount", "json_value(description, 'amount', 'money')"))
        self.assertIs(type(refusal.exception), frappe.ValidationError)

    # @feature query.error-names-operation
    def test_a_python_error_keeps_its_class_and_names_the_operation(self):
        cast = {"type": "cast", "column": {"type": "column", "column_name": "status"}, "data_type": "Money"}
        self.assert_refused(KeyError, [cast], "Operation 2 (cast): KeyError: 'Money'")

    # @feature query.expression-error-names-operation
    def test_an_expression_outside_a_build_names_the_cause_and_the_expression(self):
        """An alert evaluates its condition on a built query, outside any operation."""
        from insights.exceptions import UnknownColumn
        from insights.insights.doctype.insights_data_source_v3.ibis_utils import IbisQueryBuilder

        builder = IbisQueryBuilder(frappe._dict(name="t", operations="[]", use_live_connection=0))
        builder.query = ibis.memtable({"status": ["Open"]})
        frappe.clear_messages()
        with self.assertRaises(UnknownColumn) as refusal:
            builder.evaluate_expression("state == 'Open'")
        self.assertEqual(
            str(refusal.exception),
            "NameError: name 'state' is not defined. Expression: state == 'Open'",
        )

    # @feature query.expression-error-names-operation
    def test_a_missing_column_read_by_item_is_an_unknown_column(self):
        from insights.exceptions import UnknownColumn

        self.assert_refused(
            UnknownColumn,
            [mutate("doubled", "q['no_such_column'] * 2")],
            "Operation 2 (mutate 'doubled'): UnknownColumn: IbisTypeError: Column 'no_such_column' is not found",
            "Expression: q['no_such_column'] * 2",
        )

    # @feature query.expression-column-named-like-function
    def test_a_column_named_day_reads_as_the_column_as_a_value_and_as_the_function_when_called(self):
        query = self.build(
            rename("description", "day"),
            mutate("day_length", "day.length()"),
            mutate("day_of_date", "day(date)"),
        )

        self.assertTrue(query.schema()["day_length"].is_integer())
        self.assertTrue(query.schema()["day_of_date"].is_integer())

    # @feature query.expression-column-named-like-function
    def test_a_column_named_like_a_namespace_leaves_the_namespace_to_an_attribute_read(self):
        query = self.build(rename("description", "ibis"), mutate("one", "ibis.literal(1)"))

        self.assertTrue(query.schema()["one"].is_integer())

    # @feature query.expression-column-named-like-function
    def test_a_column_named_like_a_function_used_both_ways_is_refused_with_the_way_to_write_it(self):
        from insights.exceptions import ExpressionSyntaxError

        self.assert_refused(
            ExpressionSyntaxError,
            [rename("description", "day"), mutate("both", "day(date) + day.length()")],
            "'day' is a column and a function",
            "q['day']",
        )

    # @feature query.expression-column-named-like-io
    def test_a_column_named_like_a_reader_reads_as_a_column_bare_and_on_a_table(self):
        query = self.build(
            rename("description", "from_plan"),
            mutate("bare", "from_plan.length()"),
            mutate("on_table", "q.from_plan.length()"),
        )

        self.assertIn("bare", query.columns)
        self.assertIn("on_table", query.columns)

    # @feature query.expression-cannot-reach-files
    def test_a_column_named_like_a_writer_reaches_no_file(self):
        """A table's own method outranks its column on attribute access, and a
        bare name was once `getattr(table, name)`, the bound method."""
        import os
        import tempfile

        target = os.path.join(tempfile.gettempdir(), "insights_expression_column_probe.csv")
        from insights.exceptions import ExpressionSyntaxError

        for expression, refusal in (
            (f"to_csv({target!r})", ExpressionSyntaxError),
            (f"q.to_csv({target!r})", frappe.PermissionError),
        ):
            with self.subTest(expression=expression), self.assertRaises(refusal):
                self.build(rename("description", "to_csv"), mutate("written", expression))
            self.assertFalse(os.path.exists(target))

    # @feature query.expression-column-named-like-function
    def test_the_validator_reads_a_column_named_like_a_function_as_the_run_does(self):
        columns = json.dumps(
            [{"value": "day", "description": "String"}, {"value": "created", "description": "Datetime"}]
        )

        self.assertTrue(utils.validate_expression("day(created)", columns)["is_valid"])
        self.assertTrue(utils.validate_expression("day.length()", columns)["is_valid"])
        both = utils.validate_expression("day(created) + day.length()", columns)
        self.assertFalse(both["is_valid"])
        self.assertIn("'day' is a column and a function", both["errors"][0]["message"])

    # @feature query.expression-column-named-like-function
    def test_the_validator_reads_q_as_the_run_does(self):
        """The collision error tells the author to write `q['day']`, so the editor must accept it."""
        columns = json.dumps([{"value": "day", "description": "Integer"}])

        self.assertTrue(utils.validate_expression("q['day'] + 1", columns)["is_valid"])
        unknown = utils.validate_expression("q['nope'] + 1", columns)
        self.assertFalse(unknown["is_valid"])
        self.assertIn("Column 'nope' is not found", unknown["errors"][0]["message"])
