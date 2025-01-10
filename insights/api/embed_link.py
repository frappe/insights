import jwt
import frappe


@frappe.whitelist()
def generate_embed_link(payload):

    secret_key = frappe.db.get_single_value("Insights Settings", "secret_key")

    user_exists = frappe.db.exists("User",{"email": payload['user'], "enabled": 1})
    
    if user_exists:
        token = jwt.encode(payload, secret_key, algorithm="HS256")
        protected_link = f"{payload['resource']}?token={token}"
        return protected_link
    else:
        frappe.throw("No Access to User")
