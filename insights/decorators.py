# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from functools import wraps

import frappe


def check_role(role):
    def decorator(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            if frappe.session.user == "Administrator":
                return function(*args, **kwargs)

            if not frappe.db.exists(
                "Has Role", {"parent": frappe.session.user, "role": role}
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
            frappe.has_permission(doctype, permission_type)
            return function(*args, **kwargs)

        return wrapper

    return decorator
