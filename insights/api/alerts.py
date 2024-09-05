import frappe

from insights.decorators import insights_whitelist


@insights_whitelist()
def create_alert(alert):
    alert = frappe._dict(alert)
    alert_doc = frappe.new_doc("Insights Alert")
    alert_doc.update(alert)
    alert_doc.save()
    return alert_doc


@insights_whitelist()
def test_alert(alert):
    alert_doc = frappe.new_doc("Insights Alert")
    alert_doc.update(alert)
    should_send = alert_doc.evaluate_condition()
    if should_send:
        alert_doc.send_alert()
        return True
    return False
