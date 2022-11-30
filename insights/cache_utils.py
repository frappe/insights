# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import hashlib

import frappe

EXPIRY = 60 * 60 * 24


def make_cache_key(*args):
    key = ""
    for arg in args:
        if isinstance(arg, dict):
            key += frappe.as_json(arg)
        key += frappe.cstr(arg)
    return hashlib.md5(key.encode("utf-8")).hexdigest()


def get_or_set_cache(key, func, *args, **kwargs):
    cache = frappe.cache()
    cached_value = cache.get_value(f"insights|{key}")
    if cached_value:
        return cached_value

    expiry = kwargs.pop("expiry") if "expiry" in kwargs else EXPIRY
    value = func(*args, **kwargs)
    cache.set_value(f"insights|{key}", value, expires_in_sec=expiry)
    return value
