# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe

from contextlib import contextmanager


@contextmanager
def connect_to_db(db):
    try:
        db.connect()
        yield db
    except BaseException as e:
        frappe.log_error("Error connecting to database: {0}".format(str(e)))
    finally:
        db.close()


def insights_table_exists(datasource, tablename):
    return frappe.db.exists(
        "Insights Table", {"data_source": datasource, "table": tablename}
    )


# exception class for when query is not a select query
class NotSelectQuery(frappe.ValidationError):
    pass
