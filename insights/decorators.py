# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import threading
from functools import wraps

import frappe


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


def log_error(raise_exc=False):
    def decorator(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            try:
                return function(*args, **kwargs)
            except Exception as e:
                frappe.log_error("Insights Error")
                print(f"Error in {function.__name__}", e)
                if raise_exc:
                    raise e

        return wrapper

    return decorator


def debounce(wait):
    """Debounce decorator to be used on methods.

    - This decorator will ensure that the method is called only after
    `wait` seconds have passed since the last call.
    - The method will be called if the arguments are different from the
    last call.
    - Returns the result of the last call if the method is called again

    Parameters
    ----------
    wait : int
        Number of seconds to wait before calling the method again.

    Returns
    -------
    function
        The decorated function.

    """

    def decorator(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            # check if the method is called for the first time
            if not hasattr(function, "last_call"):
                function.last_call = threading.Event()

            # check if the arguments are different from the last call
            if (
                function.last_call.is_set()
                and function.last_args == args
                and function.last_kwargs == kwargs
                and hasattr(function, "last_result")
            ):
                return function.last_result

            # set the arguments and call the method
            function.last_args = args
            function.last_kwargs = kwargs
            function.last_call.set()
            try:
                function.last_result = function(*args, **kwargs)
                return function.last_result
            finally:
                # reset the event after `wait` seconds
                threading.Timer(wait, function.last_call.clear).start()

        return wrapper

    return decorator
