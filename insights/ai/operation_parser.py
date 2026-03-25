import json
import re

import frappe


class OperationParser:
    def __init__(self, raw_response: str):
        self.raw_response = raw_response

    def parse(self) -> list[dict]:
        operations = self._extract_operations()
        self._validate_operations(operations)
        return operations

    def _extract_operations(self) -> list[dict]:
        json_str = self._clean_response()
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            json_str = self._extract_json_block(json_str)
            return json.loads(json_str)

    def _clean_response(self) -> str:
        response = self.raw_response.strip()
        response = re.sub(r"^```json\s*", "", response)
        response = re.sub(r"^```\s*", "", response)
        response = re.sub(r"\s*```$", "", response)
        return response.strip()

    def _extract_json_block(self, text: str) -> str:
        json_match = re.search(r"\[[\s\S]*\]", text)
        if json_match:
            return json_match.group(0)
        frappe.throw("Could not parse operations from AI response")

    def _validate_operations(self, operations: list[dict]):
        if not operations:
            frappe.throw("No operations generated. Please try rephrasing your question.")

        if operations[0].get("type") != "source":
            frappe.throw("First operation must be a 'source' operation.")

        valid_types = {
            "source",
            "filter",
            "filter_group",
            "select",
            "rename",
            "remove",
            "cast",
            "join",
            "union",
            "mutate",
            "summarize",
            "order_by",
            "limit",
            "pivot_wider",
            "custom_operation",
            "sql",
            "code",
        }
        for i, op in enumerate(operations):
            op_type = op.get("type")
            if op_type not in valid_types:
                frappe.throw(f"Invalid operation type '{op_type}' at index {i}")
