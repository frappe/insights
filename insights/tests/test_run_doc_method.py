"""A document method is decided against the stored document.

`insights.api.run_doc_method` builds the document it runs from the request body,
so the body cannot also be what says who may run the method. Every rule here
names a stored document and then sends a body that claims otherwise.
"""

import frappe
from frappe.utils import set_request

from insights.api import run_doc_method
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import (
    DT,
    create_test_query,
    create_test_workbook,
    delete_users,
)
from insights.tests.permissions_utils import USER_1, USER_2, create_test_users

OWNER = USER_1
OTHER = USER_2


class StoredDocumentDecides:
    """The rules. Both `enable_permissions` settings run them."""

    ENABLE_PERMISSIONS = 0

    @classmethod
    def before_class(cls):
        create_test_users()
        cls.owner_workbook = create_test_workbook(OWNER, title="Doc Method Owner Workbook").name
        cls.owner_query = create_test_query(OWNER, cls.owner_workbook, title="Doc Method Owner Query").name
        cls.other_workbook = create_test_workbook(OTHER, title="Doc Method Other Workbook").name

    @classmethod
    def after_class(cls):
        for name in (cls.owner_workbook, cls.other_workbook):
            frappe.delete_doc(DT.WORKBOOK, name, force=True, ignore_permissions=True)
        delete_users(OWNER, OTHER)

    def before_test(self):
        self.set_team_permissions(self.ENABLE_PERMISSIONS)
        # the method surface reads the request to check the HTTP verb
        set_request(method="POST", path="/api/method/insights.api.run_doc_method")

    def export_workbook(self, name, **claims):
        return run_doc_method("export", {"doctype": DT.WORKBOOK, "name": name, **claims})

    def test_the_owner_exports_their_own_workbook(self):
        """The baseline the refusals below are measured against."""
        with self.as_user(OWNER):
            exported = self.export_workbook(self.owner_workbook)
        self.assertIn(self.owner_query, exported["dependencies"]["queries"])

    def test_another_user_cannot_export_the_workbook(self):
        with self.as_user(OTHER), self.assertRaises(frappe.PermissionError):
            self.export_workbook(self.owner_workbook)

    def test_claiming_to_own_the_workbook_does_not_grant_export(self):
        """`owner` decides access, and the body is not where it is read from."""
        with self.as_user(OTHER), self.assertRaises(frappe.PermissionError):
            self.export_workbook(self.owner_workbook, owner=OTHER)

    def test_claiming_a_workbook_does_not_grant_a_query_method(self):
        """A query's access runs through its workbook, so that link is stored too."""
        with self.as_user(OTHER), self.assertRaises(frappe.PermissionError):
            run_doc_method(
                "export",
                {
                    "doctype": DT.QUERY,
                    "name": self.owner_query,
                    "workbook": self.other_workbook,
                    "owner": OTHER,
                },
            )

    def test_calling_a_stored_document_unsaved_does_not_grant_a_method(self):
        """`__islocal` is the client saying it has nothing saved yet. A stored row
        under that name says otherwise."""
        with self.as_user(OTHER), self.assertRaises(frappe.PermissionError):
            run_doc_method(
                "export",
                {
                    "doctype": DT.QUERY,
                    "name": self.owner_query,
                    "workbook": self.other_workbook,
                    "__islocal": True,
                },
            )

    def test_a_document_the_client_has_not_saved_still_runs(self):
        """The builder runs a query before it is saved, and there is no stored
        row to decide from."""
        with self.as_user(OTHER):
            formatted = run_doc_method(
                "format",
                {
                    "doctype": DT.QUERY,
                    "name": "new-query-not-saved",
                    "workbook": self.other_workbook,
                    "is_native_query": 1,
                    "__islocal": True,
                },
                {"raw_sql": "select 1 from tabToDo"},
            )
        self.assertIn("select", formatted.lower())

    def test_a_guest_cannot_run_a_method_on_an_unsaved_document(self):
        """The unsaved path is not a way in.

        A guest holds no permission on the doctype and no Insights role, so the
        method surface refuses before a document is built. What a guest reaches is
        a public document, and an unsaved one is nobody's.
        """
        with self.as_user("Guest"), self.assertRaises(frappe.PermissionError):
            run_doc_method(
                "execute",
                {
                    "doctype": DT.QUERY,
                    "name": "new-query-not-saved",
                    "workbook": self.other_workbook,
                    "is_builder_query": 1,
                    "use_live_connection": 1,
                    "__islocal": True,
                    "operations": [
                        {
                            "type": "source",
                            "table": {
                                "type": "table",
                                "data_source": "Site DB",
                                "table_name": "tabToDo",
                            },
                        }
                    ],
                },
            )

    def test_a_filter_set_is_not_a_name(self):
        """One name is one document. A dict would reach every matching row."""
        with self.as_user(OTHER), self.assertRaises(frappe.ValidationError):
            self.export_workbook({"title": ["like", "%"]})


class TestStoredDocumentDecides(StoredDocumentDecides, InsightsIntegrationTestCase):
    ENABLE_PERMISSIONS = 0


class TestStoredDocumentDecidesWithTeamPermissions(StoredDocumentDecides, InsightsIntegrationTestCase):
    ENABLE_PERMISSIONS = 1
