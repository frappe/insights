import ast

import frappe

RESTRICTION = "Insights Resource Permission"


def execute():
    """Write a Table Restriction's `_.column` as `column`.

    A restriction names the table's columns by name, as the team form's
    example does. `_.company` is ibis's spelling, which Insights v3 never ran
    (`_` was not defined there) and Insights v4 reads as the translation
    function, so every query on the table failed. The author meant the column.
    """
    for row in frappe.get_all(
        RESTRICTION,
        filters={"table_restrictions": ("like", "%\\_.%")},
        fields=["name", "table_restrictions"],
    ):
        rewritten = without_underscore(row.table_restrictions)
        if rewritten and rewritten != row.table_restrictions:
            frappe.db.set_value(RESTRICTION, row.name, "table_restrictions", rewritten, update_modified=False)


class NameColumns(ast.NodeTransformer):
    def visit_Attribute(self, node):
        if isinstance(node.value, ast.Name) and node.value.id == "_":
            return ast.copy_location(ast.Name(id=node.attr, ctx=node.ctx), node)
        return self.generic_visit(node)


def without_underscore(expression: str) -> str | None:
    """The expression with each `_.column` as `column`, or None when it does not parse."""
    try:
        tree = ast.parse(expression.strip())
    except SyntaxError:
        return None
    return ast.unparse(NameColumns().visit(tree))
