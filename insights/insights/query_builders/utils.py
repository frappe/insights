import ast
import re


class AndOrReplacer(ast.NodeTransformer):
    """
    AST Node Transformer to replace 'and' and 'or' with 'and_(...)' and 'or_(...)' respectively.
    """

    def visit_BoolOp(self, node):
        # First, visit all children nodes
        self.generic_visit(node)

        # Check if the node is 'and' or 'or' type
        if isinstance(node.op, (ast.And, ast.Or)):
            return self._create_new_node(node)
        return node

    def _create_new_node(self, node):
        """
        Create a new node with 'and_' or 'or_' function call.
        """
        new_values = [self.visit(value) for value in node.values]
        fn_name = "and_" if isinstance(node.op, ast.And) else "or_"
        while len(new_values) > 1:
            left, right = new_values[:2]
            new_values = [self._create_call_node(fn_name, left, right)] + new_values[2:]
        return new_values[0]

    def _create_call_node(self, fn_name, left, right):
        """
        Helper method to create an ast.Call node.
        """
        return ast.Call(func=ast.Name(id=fn_name, ctx=ast.Load()), args=[left, right], keywords=[])


def replace_and_or_expressions(source_code):
    """
    Replace 'and' with 'and_' and 'or' with 'or_' in the given source code.
    """
    tree = ast.parse(source_code)
    modified_tree = AndOrReplacer().visit(tree)
    return ast.unparse(modified_tree)


def replace_equals_with_double_equals(code):
    code = code.replace("=", "==")
    code = code.replace("===", "==")
    code = code.replace("!==", "!=")
    code = code.replace(">==", ">=")
    code = code.replace("<==", "<=")
    return code


def replace_column_names(raw_expression):
    # all the columns are referred as `table_name.column_name`
    # we need to replace them with column(table_name, column_name)
    # so that we can use them in frappe.safe_eval
    # eg. `tabSales Order.name` -> column("tabSales Order", "name")
    # we have to make sure this doesn't replaces `tabSales Order`.`name` with `column("tabSales Order", "name")`
    # match only `xxx.xxx` and not `xxx`.`xxx`
    # where x can be any character except `
    match_pattern = r"`([^\`]+)\.([^\`]+)`"
    matches = re.findall(match_pattern, raw_expression)
    for match in matches:
        raw_expression = raw_expression.replace(
            f"`{match[0]}.{match[1]}`", f'column("{match[0]}", "{match[1]}")'
        )
    return raw_expression


def process_raw_expression(raw_expression):
    # replace `=` with `==` without affecting other operators
    raw_expression = replace_equals_with_double_equals(raw_expression)

    # replace column names with column function
    # eg. `tabSales Order.name` -> column("tabSales Order", "name")
    raw_expression = replace_column_names(raw_expression)

    # replace `in()` with `in_()`
    regex = r"in\s*\("
    raw_expression = re.sub(regex, "in_(", raw_expression)
    # the above regex also replaces `not_in()` with `not_in_()` which is not required
    # so we replace `not_in_()` with `not_in()` again
    raw_expression = raw_expression.replace("not_in_(", "not_in(")

    raw_expression = raw_expression.replace("&&", " and ")
    raw_expression = raw_expression.replace("||", " or ")
    raw_expression = replace_and_or_expressions(raw_expression)

    return raw_expression
