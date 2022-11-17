# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe

from insights.setup.demo import DemoDataFactory


def execute():
    factory = DemoDataFactory().run(force=True)

    if not factory.demo_data_exists():
        frappe.throw("Demo data not imported")

    demo_tables = [
        "Customers",
        "Geolocation",
        "OrderItems",
        "OrderPayments",
        "OrderReviews",
        "Orders",
        "Products",
        "Sellers",
    ]

    InsightsTable = frappe.qb.DocType("Insights Table")
    (
        frappe.qb.update(InsightsTable)
        .set(InsightsTable.data_source, "Demo Data")
        .where(InsightsTable.name.isin(demo_tables))
        .run()
    )

    InsightsQuery = frappe.qb.DocType("Insights Query")
    InsightsQueryTable = frappe.qb.DocType("Insights Query Table")
    queries = (
        frappe.qb.from_(InsightsQuery)
        .join(InsightsQueryTable)
        .on(InsightsQuery.name == InsightsQueryTable.parent)
        .select(InsightsQuery.name)
        .distinct()
        .where(InsightsQueryTable.table.isin(demo_tables))
        .run(pluck="name")
    )

    if queries:
        (
            frappe.qb.update(InsightsQuery)
            .set(InsightsQuery.data_source, "Demo Data")
            .where(InsightsQuery.name.isin(queries))
            .run()
        )
