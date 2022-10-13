# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from typing import Protocol

from insights.insights.doctype.insights_query.insights_query import InsightsQuery


class QueryBuilder(Protocol):
    def build(self, query: InsightsQuery):
        ...
