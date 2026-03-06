import frappe

from insights.decorators import insights_whitelist


@insights_whitelist()
def get_notebooks():
    return frappe.get_list(
        "Insights Notebook",
        fields=["name", "title", "creation", "modified"],
        filters={"owner": frappe.session.user},
        order_by="creation desc",
    )


@insights_whitelist()
def create_notebook(title: str):
    notebook = frappe.new_doc("Insights Notebook")
    notebook.title = title
    notebook.save()
    return notebook.name


@insights_whitelist()
def create_notebook_page(notebook: str):
    if not frappe.has_permission("Insights Notebook", "write", notebook):
        frappe.throw("Not permitted", frappe.PermissionError)
    notebook_page = frappe.new_doc("Insights Notebook Page")
    notebook_page.notebook = notebook
    notebook_page.title = "Untitled"
    notebook_page.save()
    return notebook_page.name


@insights_whitelist()
def get_notebook_pages(notebook: str):
    if not frappe.has_permission("Insights Notebook", "read", notebook):
        frappe.throw("Not permitted", frappe.PermissionError)
    return frappe.get_list(
        "Insights Notebook Page",
        filters={"notebook": notebook},
        fields=["name", "title", "creation", "modified"],
        order_by="creation desc",
    )
