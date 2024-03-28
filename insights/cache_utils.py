# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import hashlib

import frappe

EXPIRY = 60 * 10


def make_digest(*args):
    key = ""
    for arg in args:
        if isinstance(arg, dict):
            key += frappe.as_json(arg)
        key += frappe.cstr(arg)
    return hashlib.md5(key.encode("utf-8")).hexdigest()


def get_or_set_cache(key, func, force=False, expiry=EXPIRY):
    key = f"insights|{key}"
    cached_value = frappe.cache().get_value(key)
    if cached_value is not None and not force:
        return cached_value

    value = func()
    frappe.cache().set_value(key, value, expires_in_sec=expiry)
    return value


@frappe.whitelist()
def reset_insights_cache():
    frappe.only_for("System Manager")
    frappe.cache().delete_keys("insights*")
