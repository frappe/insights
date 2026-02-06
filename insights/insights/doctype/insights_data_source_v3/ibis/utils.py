import ast
import json
import re
import sys
import traceback

import frappe
import ibis
import ibis.expr.types as ir
from ibis import selectors as s
from jedi import Script


def get_functions():
    import insights.insights.doctype.insights_data_source_v3.ibis.functions as functions

    context = frappe._dict()
    exclude_keys = [
        "frappe",
        "ibis",
        "ir",
        "math",
        "s",
    ]
    for key in dir(functions):
        if not key.startswith("_") and key not in exclude_keys:
            context[key] = getattr(functions, key)

    selectors = frappe._dict()
    for key in get_whitelisted_selectors():
        selectors[key] = getattr(s, key)

    context["s"] = selectors
    context["selectors"] = selectors

    allowed_ibis_attributes = (
        "array",
        "asc",
        "cases",
        "coalesce",
        "cross_join",
        "cume_dist",
        "cumulative_window",
        "date",
        "dense_rank",
        "desc",
        "difference",
        "dtype",
        "following",
        "greatest",
        "ifelse",
        "infer_dtype",
        "infer_schema",
        "intersect",
        "interval",
        "join",
        "least",
        "literal",
        "map",
        "memtable",
        "now",
        "ntile",
        "null",
        "and_",
        "or_",
        "param",
        "parse_sql",
        "percent_rank",
        "pi",
        "preceding",
        "random",
        "range",
        "range_window",
        "rank",
        "read_csv",
        "read_delta",
        "read_json",
        "read_parquet",
        "row_number",
        "rows_window",
        "schema",
        "selectors",
        "struct",
        "table",
        "time",
        "timestamp",
        "to_sql",
        "today",
        "trailing_range_window",
        "trailing_window",
        "union",
        "uuid",
        "watermark",
        "window",
    )
    context.ibis = frappe._dict()
    for attr in allowed_ibis_attributes:
        context.ibis[attr] = getattr(ibis, attr)

    return context


def get_whitelisted_selectors():
    # all the selectors that are decorated with @public
    # are added to __all__ in the selectors module
    # check: ibis.selectors.py & public.py
    try:
        whitelisted_selectors = s.__dict__["__all__"]
    except KeyError:
        whitelisted_selectors = []
    return whitelisted_selectors


@frappe.whitelist()
def get_function_list():
    return [key for key in get_functions() if not key.startswith("_")]


@frappe.whitelist()
def get_code_completions(code: str, column_options=None):
    import_statement = """from insights.insights.doctype.insights_data_source_v3.ibis.functions import *\nfrom ibis import selectors as s"""
    code = f"{import_statement}\n\n{code}"

    cursor_pos = code.find("|")
    line_pos = code.count("\n", 0, cursor_pos)
    column_pos = cursor_pos - code.rfind("\n", 0, cursor_pos) - 1
    code = code.replace("|", "")

    column_types = {}
    if column_options:
        try:
            columns = json.loads(column_options)
            column_types = {
                col.get("value"): col.get("data_type", "Unknown") for col in columns if col.get("value")
            }
        except (json.JSONDecodeError, TypeError):
            pass

    current_function = None

    script = Script(code)
    signature_items = script.get_signatures(line_pos + 1, column_pos)
    for sig in signature_items:
        description = sig.docstring()
        # check if description is empty or only contains a single line
        if not description or "\n" not in description:
            current_function = {"name": sig.name}
            continue

        # remove the standard definition from the description, i.e first line
        description = description.split("\n", 1)[1].strip()

        # use custom definition, if "def " is present in the docstring
        definition = ""
        if "def " in description:
            definition = description.split("\n", 1)[0].strip()
            description = description.replace(definition, "").strip()
            definition = definition.replace("def ", "")

        current_function = {
            "name": sig.name,
            "definition": definition,
            "description": description,
            "params": [{"name": param.name, "description": param.description} for param in sig.params],
        }
        if sig.index is not None:
            current_param = sig.params[sig.index]
            current_function["current_param"] = current_param.name
            current_function["current_param_description"] = current_param.description

            # add column type if the current parameter is a column
            if current_param.name in column_types:
                current_function["current_param_type"] = column_types[current_param.name]

    return {
        "current_function": current_function,
        "column_types": column_types,
    }


@frappe.whitelist()
def get_function_description(funcName: str):
    functions_dict = get_functions()
    func_obj = functions_dict.get(funcName)

    if not func_obj:
        return None

    docstring = getattr(func_obj, "__doc__", "") or ""

    if "def " in docstring:
        lines = docstring.split("\n", 1)
        definition = lines[0].replace("def ", "").strip()
        description = lines[1].strip() if len(lines) > 1 else ""

    return {"name": funcName, "definition": definition, "description": description}


def parse_column_metadata(column_options: str):
    columns = frappe.parse_json(column_options) or []
    meta = [col for col in columns if col.get("value")]
    return meta


def create_error(line: int, column: int, message: str, hint: str = None):
    error = {"line": line, "column": column, "message": message}
    if hint:
        error["hint"] = hint
    return error


def get_ibis_dtype(columns: list[dict]):
    type_mapping = {
        "String": "string",
        "Integer": "int64",
        "Decimal": "float64",
        "Date": "date",
        "Datetime": "timestamp",
        "Time": "time",
        "Text": "string",
        "JSON": "json",
        "Array": "array<json>",
        "Auto": "",
    }
    return {
        col.get("value"): type_mapping.get(col.get("description"))
        for col in columns
        if col.get("value") and col.get("description")
    }


def find_similar_names(name: str, names: set[str]):
    name_lower = name.lower()
    return [c for c in names if name_lower in c.lower() or c.lower() in name_lower]


def validate_syntax(expression: str):
    try:
        ast.parse(expression)
        return {"is_valid": True, "errors": []}
    except SyntaxError as e:
        error = create_error(line=e.lineno or 1, column=e.offset or 0, message=f"Syntax error: {e.msg}")
        return {"is_valid": False, "errors": [error]}


def is_function(node, tree):
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            if child == node:
                return isinstance(parent, ast.Call) and parent.func == node
    return False


def validate_function_name(node, available_functions: set[str]):
    func_name = node.func.id
    if func_name in available_functions:
        return None

    suggestions = find_similar_names(func_name, available_functions)
    suggestion_text = f"Did you mean: {', '.join(suggestions[:2])}?" if suggestions else ""

    return create_error(
        line=node.lineno,
        column=node.col_offset,
        message=f"Unknown function '{func_name}'. {suggestion_text}".strip(),
    )


def validate_variable_name(node, tree, available_functions: set[str], available_columns: set[str]):
    var_name = node.id

    if var_name in available_functions or var_name in available_columns:
        return None

    # pass if the variable is being assigned (LHS)
    # perf: this is faster and more accurate than looping
    # ctx is Store if the container is an assignment target
    if isinstance(node.ctx, ast.Store):
        return None

    if is_function(node, tree):
        return None

    suggestions = find_similar_names(var_name, available_columns)
    suggestion_text = f"Did you mean: {', '.join(suggestions[:2])}?" if suggestions else ""

    return create_error(
        line=node.lineno,
        column=node.col_offset,
        message=f"Column '{var_name}' not found. {suggestion_text}".strip(),
    )


def validate_names(tree, columns: list[dict]):
    functions = get_functions()
    available_functions = set(functions.keys())
    available_columns = {col.get("value") for col in columns}

    errors = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            error = validate_function_name(node, available_functions)
            if error:
                errors.append(error)

        if isinstance(node, ast.Name):
            error = validate_variable_name(node, tree, available_functions, available_columns)
            if error:
                errors.append(error)

    return {"is_valid": len(errors) == 0, "errors": errors}


def eval_script(table, schema: dict[str, str]):
    script = get_functions()
    for col_name in schema:
        script[col_name] = getattr(table, col_name)
    return script


# Functions that are not supported by certain column types like `DateColumn.sum()`
def handle_attribute_error(error: AttributeError, line: int = 1):
    obj = getattr(error, "obj", None)
    attr_name = getattr(error, "name", None)
    error_msg = str(error)

    if "'NoneType' object has no attribute" in error_msg:
        message = "Type error: count() missing 1 required positional argument: 'column'"
        return create_error(line=line, column=0, message=message)

    if obj is None or attr_name is None:
        return create_error(line=line, column=0, message=f"Type error: {error_msg}")

    message = f"Type error: {error_msg}"
    hint = None

    if isinstance(obj, ir.Expr):
        dtype = obj.type()

        # Check if this method exists on a COLUMN of this type
        try:
            mock_table = ibis.table({"mock": dtype}, name="validation_mock")
            mock_col = mock_table["mock"]
            has_method_on_col = hasattr(mock_col, attr_name)
        except Exception:
            has_method_on_col = False

        if isinstance(obj, ir.Scalar):
            if has_method_on_col:
                message = f"Type error: Cannot call aggregation '{attr_name}()' on a scalar value."
                hint = (
                    f"Hint: '{attr_name}' expects a column but you are applying it to a single value "
                )
            else:
                message = f"Type error: '{dtype}' data does not support '{attr_name}()'."

        elif isinstance(obj, ir.Column):
            message = f"Type error: '{dtype}' columns do not support '{attr_name}()'."

    return create_error(line=line, column=0, message=message, hint=hint)

def validate_types(expression: str, columns: list[dict]):
    schema = get_ibis_dtype(columns)
    if not schema:
        return {"is_valid": True, "errors": []}

    try:
        validation_table = ibis.table(schema, name="validation_table")
        eval_context = eval_script(validation_table, schema)
        exec(expression, {"__builtins__": {}}, eval_context)
        return {"is_valid": True, "errors": []}

    except (AttributeError, TypeError) as e:
        _,_,tb = sys.exc_info()
        line = get_error_line(tb)
        error_msg = str(e)

        if isinstance(e, AttributeError):
            error = handle_attribute_error(e, line)
            return {"is_valid": False, "errors": [error]}

        # for <function count at 0x...>
        if "Unable to infer datatype" in error_msg and "<function" in error_msg:
            match = re.search(r"<function (\w+)", error_msg)
            func_name = match.group(1) if match else "unknown"

            msg = f"Type error: You are trying to do math with the function '{func_name}' itself."
            hint = f"Hint: Did you forget parentheses? Try '{func_name}()' instead of '{func_name}'."

            return {"is_valid": False, "errors": [create_error(line, 0, msg, hint=hint)]}

        return {"is_valid": False, "errors": [create_error(line, 0, f"Type error: {error_msg}")]}

    except Exception as e:
        _,_,tb = sys.exc_info()
        line = get_error_line(tb)
        frappe.log_error(f"Unexpected validation error: {str(e)}")
        return {"is_valid": False, "errors": [create_error(line, 0, f"Error: {str(e)}")]}

def get_error_line(tb) -> int:
    if tb:
        for frame in traceback.extract_tb(tb):
            if frame.filename == "<string>":
                return frame.lineno
    return 1
@frappe.whitelist()
def validate_expression(expression: str, column_options: str):
    """Main function to validate expression/syntax"""

    if not expression.strip():
        return {"is_valid": True, "errors": []}

    columns = parse_column_metadata(column_options)
    syntax_result = validate_syntax(expression)
    if not syntax_result["is_valid"]:
        return syntax_result

    tree = ast.parse(expression)
    name_result = validate_names(tree, columns)
    if not name_result["is_valid"]:
        return name_result

    type_result = validate_types(expression, columns)
    return type_result
