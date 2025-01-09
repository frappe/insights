import jwt
import frappe


@frappe.whitelist()
def generate_embed_link(payload):

    secret_key = frappe.db.get_single_value("Insights Settings", "secret_key")

    users = frappe.get_all(
        "User",
        filters={
            "enabled": 1,
        },
        fields=["email"],
    )

    user_exists = any(user["email"] == payload["user"] for user in users)
    if user_exists:
        token = jwt.encode(payload, secret_key, algorithm="HS256")
        protected_link = f"{payload['resource']}?token={token}"
        return protected_link
    else:
        frappe.throw("No Access to User")
