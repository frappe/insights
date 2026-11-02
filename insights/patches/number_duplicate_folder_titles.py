import frappe

from insights.insights.doctype.insights_folder.insights_folder import next_free_title

FOLDER = "Insights Folder"


def execute():
    """Number apart the folders of one type that share a title in a workbook.

    A file names a folder by its title, so a copy, a paste or a restore folds
    them into one. `InsightsFolder.validate_title` now keeps a new pair from
    forming; this numbers the pairs written before it, the oldest keeping its
    title.
    """
    folders = frappe.get_all(
        FOLDER, fields=["name", "workbook", "type", "title"], order_by="creation asc, name asc"
    )

    taken: dict[tuple[str, str], set[str]] = {}
    for folder in folders:
        taken.setdefault((folder.workbook, folder.type), set()).add(folder.title)

    seen: set[tuple[str, str, str]] = set()
    for folder in folders:
        key = (folder.workbook, folder.type, folder.title)
        if key not in seen:
            seen.add(key)
            continue
        titles = taken[(folder.workbook, folder.type)]
        title = next_free_title(folder.title, titles)
        titles.add(title)
        frappe.db.set_value(FOLDER, folder.name, "title", title, update_modified=False)
