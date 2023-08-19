# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import time
from functools import cached_property

import frappe
from frappe import _dict
from frappe.model.document import Document
from frappe.utils import flt

from insights.decorators import log_error
from insights.insights.doctype.insights_data_source.sources.utils import (
    create_insights_table,
)
from insights.utils import InsightsChart, InsightsSettings, InsightsTable, ResultColumn

from ..insights_data_source.sources.query_store import sync_query_store
from .insights_assisted_query import InsightsAssistedQueryController
from .insights_legacy_query import (
    InsightsLegacyQueryClient,
    InsightsLegacyQueryController,
)
from .insights_query_client import InsightsQueryClient
from .insights_raw_query import InsightsRawQueryController
from .insights_script_query import InsightsScriptQueryController
from .utils import (
    CachedResults,
    InsightsTableColumn,
    Status,
    apply_pivot_transform,
    apply_transpose_transform,
    apply_unpivot_transform,
    export_query,
)


class InsightsQuery(InsightsLegacyQueryClient, InsightsQueryClient, Document):
    def before_validate(self):
        if not self.title and self.name:
            self.title = self.name.replace("-", " ").replace("QRY", "Query")

    def before_save(self):
        self.variant_controller.before_save()

    def on_update(self):
        self.create_default_chart()
        self.update_query_store()
        self.update_linked_docs()

    def on_trash(self):
        self.delete_insights_table()
        self.delete_default_chart()

    @property
    def is_saved_as_table(self):
        table_name = frappe.db.exists("Insights Table", {"table": self.name, "is_query_based": 1})
        return bool(table_name)

    @property
    def results(self):
        fetch_if_not_cached = self.status == Status.SUCCESS.value
        limit = InsightsSettings.get("query_result_limit") or 1000
        try:
            results = self.retrieve_results(fetch_if_not_cached)
        except Exception:
            results = []
        return frappe.as_json(results[:limit])

    @property
    def results_row_count(self):
        return len(CachedResults.get(self.name))

    @cached_property
    def variant_controller(self):
        if self.is_native_query:
            return InsightsRawQueryController(self)
        if self.is_assisted_query:
            return InsightsAssistedQueryController(self)
        if self.is_script_query:
            return InsightsScriptQueryController(self)
        return InsightsLegacyQueryController(self)

    def validate(self):
        self.variant_controller.validate()

    def reset(self):
        new_query = frappe.new_doc("Insights Query")
        new_query.name = self.name
        new_query.title = self.name.replace("-", " ").replace("QRY", "Query")
        new_query.data_source = self.data_source
        new_query.is_native_query = self.is_native_query
        new_query.is_assisted_query = self.is_assisted_query
        new_query.is_script_query = self.is_script_query
        new_query_dict = new_query.as_dict(no_default_fields=True)
        self.update(new_query_dict)
        self.status = Status.SUCCESS.value
        CachedResults.set(self.name, [])
        self.after_reset()

    def after_reset(self):
        if not hasattr(self.variant_controller, "after_reset"):
            return
        self.variant_controller.after_reset()

    def create_default_chart(self):
        if frappe.db.exists("Insights Chart", {"query": self.name}):
            return
        chart = frappe.new_doc("Insights Chart")
        chart.query = self.name
        chart.save(ignore_permissions=True)

    def update_insights_table(self, force=False):
        if not self.is_saved_as_table and not force:
            return
        query_table = _dict(
            table=self.name,
            label=self.title,
            is_query_based=1,
            data_source=self.data_source,
            columns=InsightsTableColumn.from_dicts(
                self.get_columns(),
            ),
        )
        create_insights_table(query_table)

    def get_columns(self):
        return self.get_columns_from_results(self.retrieve_results())

    def update_query_store(self):
        if not self.is_stored:
            return
        sync_query_store([self.name], force=True)

    def update_linked_docs(self):
        old_self = self.get("_doc_before_save")
        old_title = old_self.title if old_self else None
        if not old_title or old_title == self.title:
            return

        table = frappe.qb.DocType("Insights Table")
        _ = (
            frappe.qb.update(table)
            .set(table.label, self.title)
            .where(table.table == self.name)
            .run()
        )

    def delete_insights_table(self):
        table_name = InsightsTable.get_name(table=self.name)
        frappe.delete_doc_if_exists("Insights Table", table_name)

    def delete_default_chart(self):
        chart_name = InsightsChart.get_name(query=self.name)
        frappe.delete_doc_if_exists("Insights Chart", chart_name)

    def retrieve_results(self, fetch_if_not_cached=False):
        results = CachedResults.get(self.name)
        if results is None and fetch_if_not_cached:
            results = self.fetch_results()
        return results or []

    def fetch_results(self):
        self.before_fetch()

        self._results = []
        start = time.monotonic()
        try:
            self._results = self.variant_controller.fetch_results()
            self._results = self.after_fetch(self._results)
            self._results = self.process_results_columns(self._results)
            self.db_set(
                {
                    "status": Status.SUCCESS.value,
                    "execution_time": flt(time.monotonic() - start, 3),
                    "last_execution": frappe.utils.now(),
                },
                update_modified=False,
                commit=True,
            )
        except Exception as e:
            frappe.db.rollback()
            frappe.log_error(str(e)[:140])
            self.db_set("status", Status.FAILED.value, commit=True)
            raise
        finally:
            CachedResults.set(self.name, self._results)
            self.update_insights_table()
        return self._results

    def before_fetch(self):
        self.variant_controller.before_fetch()

    @log_error(raise_exc=True)
    def process_results_columns(self, results):
        if not results:
            return results
        results[0] = ResultColumn.from_dicts(self.get_columns_from_results(results))
        return results

    def get_columns_from_results(self, results):
        return self.variant_controller.get_columns_from_results(results)

    def after_fetch(self, results):
        if self.transforms:
            results = self.apply_transforms(results)
        results = self.variant_controller.after_fetch(results)
        return results

    def apply_transforms(self, results):
        self.validate_transforms()
        for transform in self.transforms:
            if transform.type == "Pivot":
                return apply_pivot_transform(results, transform.options)
            if transform.type == "Unpivot":
                return apply_unpivot_transform(results, transform.options)
            if transform.type == "Transpose":
                return apply_transpose_transform(results, transform.options)

    def validate_transforms(self):
        pivot_transforms = [t for t in self.transforms if t.type == "Pivot"]
        unpivot_transforms = [t for t in self.transforms if t.type == "Unpivot"]
        transpose_transforms = [t for t in self.transforms if t.type == "Transpose"]

        if len(pivot_transforms) > 1:
            frappe.throw("Only one Pivot transform is allowed")
        if len(unpivot_transforms) > 1:
            frappe.throw("Only one Unpivot transform is allowed")
        if len(transpose_transforms) > 1:
            frappe.throw("Only one Transpose transform is allowed")
        if pivot_transforms and unpivot_transforms:
            frappe.throw("Pivot and Unpivot transforms cannot be used together")
        if pivot_transforms and transpose_transforms:
            frappe.throw("Pivot and Transpose transforms cannot be used together")
        if unpivot_transforms and transpose_transforms:
            frappe.throw("Unpivot and Transpose transforms cannot be used together")

    @frappe.whitelist()
    def get_tables_columns(self):
        return self.variant_controller.get_tables_columns()

    def get_selected_tables(self):
        return self.variant_controller.get_selected_tables()

    def export(self):
        return export_query(self)
