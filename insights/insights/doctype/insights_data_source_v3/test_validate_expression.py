# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import json
import unittest

from frappe.utils.safe_exec import is_safe_exec_enabled

from insights.insights.doctype.insights_data_source_v3.ibis import utils

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

    def test_bare_dunder_access_is_rejected(self):
        result = self._validate("amount.__class__.__base__")
        self.assertFalse(result["is_valid"])

    # --- functionality: legit validation behaviour is preserved ---

    def test_unknown_column_reports_friendly_error(self):
        result = self._validate("foo + 1")
        self.assertFalse(result["is_valid"])
        self.assertIn("foo", result["errors"][0]["message"])

    def test_syntax_error_is_reported(self):
        result = self._validate("amount +")
        self.assertFalse(result["is_valid"])
        self.assertIn("Syntax error", result["errors"][0]["message"])

    def test_empty_expression_is_valid(self):
        self.assertTrue(self._validate("   ")["is_valid"])

    @unittest.skipUnless(is_safe_exec_enabled(), "expression execution requires server scripts enabled")
    def test_valid_expression_passes(self):
        result = self._validate("amount.sum()")
        self.assertTrue(result["is_valid"], result)
