import frappe


@frappe.whitelist()
def get_notebooks():
    # TODO: Add permission check
    return frappe.get_list(
        "Insights Notebook",
        fields=["name", "title", "creation", "modified"],
        order_by="creation desc",
    )


@frappe.whitelist()
def create_notebook(title):
    notebook = frappe.new_doc("Insights Notebook")
    notebook.title = title
    notebook.save()
    return notebook.name


@frappe.whitelist()
def create_notebook_page(notebook):
    notebook_page = frappe.new_doc("Insights Notebook Page")
    notebook_page.notebook = notebook
    notebook_page.title = "Untitled"
    notebook_page.save()
    return notebook_page.name


@frappe.whitelist()
def get_notebook_pages(notebook):
    return frappe.get_list(
        "Insights Notebook Page",
        filters={"notebook": notebook},
        fields=["name", "title", "creation", "modified"],
        order_by="creation desc",
    )
