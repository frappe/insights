# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from functools import wraps
from typing import Callable

import frappe
from frappe.utils.caching import __generate_request_cache_key


def check_role(role):
    def decorator(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            if frappe.session.user == "Administrator":
                return function(*args, **kwargs)

            perm_disabled = not frappe.db.get_single_value(
                "Insights Settings", "enable_permissions"
            )
            if perm_disabled and role in ["Insights Admin", "Insights User"]:
                return function(*args, **kwargs)

            if not frappe.db.get_value(
                "Has Role",
                {"parent": frappe.session.user, "role": role},
                cache=not frappe.flags.in_test,
            ):
                frappe.throw(
                    frappe._("You do not have permission to access this resource"),
                    frappe.PermissionError,
                )

            return function(*args, **kwargs)

        return wrapper

    return decorator


def check_permission(doctype, permission_type="read"):
    def decorator(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            frappe.has_permission(doctype, permission_type, throw=True)
            return function(*args, **kwargs)

        return wrapper

    return decorator


def log_error():
    def decorator(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            try:
                return function(*args, **kwargs)
            except BaseException:
                frappe.log_error("Insights Error")

        return wrapper

    return decorator
