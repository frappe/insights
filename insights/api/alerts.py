import frappe

from insights.decorators import insights_whitelist, validate_type


@insights_whitelist()
@validate_type
def get_alerts(query: str):
    return frappe.get_list(
        "Insights Alert",
        filters={"query": query},
        fields=["*"],
    )
