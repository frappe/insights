# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
import pandas as pd
from frappe.integrations.utils import make_get_request, make_post_request
from frappe.utils.safe_exec import safe_exec

from .sqlite import SQLiteDB


class RestAPIDB(SQLiteDB):
    def import_table(self, import_doc):
        raise NotImplementedError

    def sync_tables(self, tables=None, force=False):
        self.import_tables()
        with self.engine.begin() as connection:
            self.table_factory.sync_tables(connection, tables, force)

    def import_tables(self):
        data_source_doc = frappe.get_cached_doc(
            "Insights Data Source", self.data_source
        )
        for request in data_source_doc.requests:
            self.import_request_data_to_table(request)

    def import_request_data_to_table(self, request):
        data = self.make_request(
            url=f"{request.endpoint}",
            method=request.method,
            headers=frappe.parse_json(request.headers),
            body=frappe.parse_json(request.body),
        )
        if request.post_process:
            locals_dict = {"response": data}
            safe_exec(request.post_process, None, locals_dict)
            data = locals_dict["response"]

        df = pd.DataFrame(data)
        df.columns = [frappe.scrub(c) for c in df.columns]
        df.to_sql(
            name=request.title,
            con=self.engine,
            index=False,
            if_exists="replace",
        )

    def make_request(self, url, method="GET", headers=None, body=None):
        try:
            if method == "GET":
                return make_get_request(url, headers=headers)
            elif method == "POST":
                return make_post_request(url, headers=headers, data=body)
        except Exception as e:
            frappe.log_error("Error while making request")
            frappe.throw(f"Error while making request to {url}: {e}")
