import frappe
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
def get_code_completions(code: str):
    import_statement = """from insights.insights.doctype.insights_data_source_v3.ibis.functions import *\nfrom ibis import selectors as s"""
    code = f"{import_statement}\n\n{code}"

    cursor_pos = code.find("|")
    line_pos = code.count("\n", 0, cursor_pos)
    column_pos = cursor_pos - code.rfind("\n", 0, cursor_pos) - 1
    code = code.replace("|", "")

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
            "params": [
                {"name": param.name, "description": param.description}
                for param in sig.params
            ],
        }
        if sig.index is not None:
            current_param = sig.params[sig.index]
            current_function["current_param"] = current_param.name
            current_function["current_param_description"] = current_param.description

    return {
        "current_function": current_function,
    }
