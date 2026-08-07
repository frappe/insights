import frappe


def execute():
    """The workbook template channel is gone; its copies stay, as user documents.

    A copy was always user-editable, so it was already a fork — nothing about it
    has to change for it to keep working, and nothing here touches its contents,
    its ownership or the organization share it was given. What retires with the
    channel is the update model that watched it: `imported_version` and
    `imported_checksum` are how a shipped version was compared against a copy,
    and no shipped version exists to compare against any more.

    The two fields are off the doctype, so their columns are orphans — blanked
    here rather than left holding a fingerprint of a release that has retired.
    Raw SQL because the fields are no longer in the meta the ORM writes through.

    `from_template` stays. It is the only record of where a copy came from, and
    it decides nothing: a copy is not a duplicate of anything this site ships,
    so it gets no provenance `standard_id` either — the bundles carry per-document
    identities that the copy's documents never held.
    """
    doctype = "Insights Workbook"
    # the empty value of each column's own type — an orphan column is still NOT NULL
    retired = {"imported_version": 0, "imported_checksum": ""}
    columns = [column for column in retired if frappe.db.has_column(doctype, column)]
    if not columns:
        return

    assignments = ", ".join(f"`{column}` = %s" for column in columns)
    frappe.db.sql(
        f"update `tab{doctype}` set {assignments}",  # nosemgrep — orphan columns, no meta to write through
        tuple(retired[column] for column in columns),
    )
