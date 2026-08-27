"""A data source's credentials are readable only by the roles that configure it.

Reading a data source and reading how it connects are two different grants. The
generic document routes — `/api/resource`, `frappe.client.get`, `get_list` with a
field list — return whatever the doctype exposes, so the boundary has to live on
the fields themselves rather than on the endpoints that read them.

`Password` fields already mask themselves. These four do not, so they carry a
permlevel instead.
"""

import frappe

from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import DT, create_user, delete_users

ADMIN = "credentials_admin@test.com"
USER = "credentials_user@test.com"

CREDENTIAL_FIELDS = (
    "connection_string",
    "bigquery_service_account_key",
    "http_headers",
    "api_custom_headers",
)

CONNECTION_STRING = "postgresql://svc:hunter2@warehouse.internal:5432/analytics"
SERVICE_ACCOUNT_KEY = '{"type": "service_account", "private_key": "-----BEGIN PRIVATE KEY-----"}'


class TestDataSourceCredentials(InsightsIntegrationTestCase):
    @classmethod
    def before_class(cls):
        create_user(ADMIN, first_name="Credentials", last_name="Admin", roles="Insights Admin")
        create_user(USER, first_name="Credentials", last_name="User", roles="Insights User")
        cls.data_source = (
            frappe.get_doc(
                {
                    "doctype": DT.DATA_SOURCE,
                    "title": "Credentials Test Source",
                    "database_type": "PostgreSQL",
                    "database_name": "analytics",
                    "connection_string": CONNECTION_STRING,
                    "bigquery_service_account_key": SERVICE_ACCOUNT_KEY,
                }
            )
            .insert()
            .name
        )

    @classmethod
    def after_class(cls):
        frappe.delete_doc(DT.DATA_SOURCE, cls.data_source, force=True, ignore_permissions=True)
        delete_users(ADMIN, USER)

    def read_as(self, user):
        with self.as_user(user):
            doc = frappe.get_doc(DT.DATA_SOURCE, self.data_source)
            doc.apply_fieldlevel_read_permissions()
            return doc

    def test_an_insights_user_reads_no_credential_field(self):
        doc = self.read_as(USER)
        for fieldname in CREDENTIAL_FIELDS:
            self.assertIsNone(doc.get(fieldname), f"{fieldname} reached an Insights User")

    def test_an_insights_admin_still_reads_the_credentials(self):
        doc = self.read_as(ADMIN)
        self.assertEqual(doc.connection_string, CONNECTION_STRING)
        self.assertEqual(doc.bigquery_service_account_key, SERVICE_ACCOUNT_KEY)

    def test_a_credential_field_is_dropped_from_a_list_field_list(self):
        with self.as_user(USER):
            rows = frappe.get_list(
                DT.DATA_SOURCE,
                filters={"name": self.data_source},
                fields=["name", "connection_string"],
            )
        self.assertEqual(rows, [{"name": self.data_source}])

    def test_the_generic_document_route_returns_no_credentials(self):
        """`frappe.client.get` is what `/api/resource/<doctype>/<name>` calls."""
        import frappe.client

        with self.as_user(USER):
            doc = frappe.client.get(DT.DATA_SOURCE, self.data_source)
        for fieldname in CREDENTIAL_FIELDS:
            self.assertIsNone(doc.get(fieldname), f"{fieldname} reached an Insights User")

    def test_the_title_stays_readable(self):
        """The permlevel bounds the credentials, not the document."""
        with self.as_user(USER):
            self.assertEqual(
                frappe.get_list(DT.DATA_SOURCE, filters={"name": self.data_source}, pluck="title"),
                ["Credentials Test Source"],
            )
