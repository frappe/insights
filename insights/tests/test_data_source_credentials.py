"""A data source's credentials are readable only by the roles that configure it.

Reading a data source and reading how it connects are two different grants. The
generic document routes — `/api/resource`, `frappe.client.get`, `get_list` with a
field list — return whatever the doctype exposes, so the boundary has to live on
the fields themselves rather than on the endpoints that read them.

`Password` fields already mask themselves. These four do not, so they have a
permlevel instead.
"""

import unittest
from unittest.mock import MagicMock, patch

import duckdb
import frappe
from frappe.utils import set_request

from insights.api import run_doc_method
from insights.insights.doctype.insights_data_source_v3.connectors.duckdb import get_http_secret
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

    # @feature data-source.credentials-stay-with-admins
    def test_an_insights_user_reads_no_credential_field(self):
        doc = self.read_as(USER)
        for fieldname in CREDENTIAL_FIELDS:
            self.assertIsNone(doc.get(fieldname), f"{fieldname} reached an Insights User")

    # @feature data-source.credentials-stay-with-admins
    def test_an_insights_admin_still_reads_the_credentials(self):
        doc = self.read_as(ADMIN)
        self.assertEqual(doc.connection_string, CONNECTION_STRING)
        self.assertEqual(doc.bigquery_service_account_key, SERVICE_ACCOUNT_KEY)

    # @feature data-source.credentials-stay-with-admins
    def test_a_credential_field_is_dropped_from_a_list_field_list(self):
        with self.as_user(USER):
            rows = frappe.get_list(
                DT.DATA_SOURCE,
                filters={"name": self.data_source},
                fields=["name", "connection_string"],
            )
        self.assertEqual(rows, [{"name": self.data_source}])

    # @feature data-source.credentials-stay-with-admins
    def test_the_generic_document_route_returns_no_credentials(self):
        """`frappe.client.get` is what `/api/resource/<doctype>/<name>` calls."""
        import frappe.client

        with self.as_user(USER):
            doc = frappe.client.get(DT.DATA_SOURCE, self.data_source)
        for fieldname in CREDENTIAL_FIELDS:
            self.assertIsNone(doc.get(fieldname), f"{fieldname} reached an Insights User")

    # @feature data-source.credentials-stay-with-admins
    def test_the_title_stays_readable(self):
        """The permlevel bounds the credentials, not the document."""
        with self.as_user(USER):
            self.assertEqual(
                frappe.get_list(DT.DATA_SOURCE, filters={"name": self.data_source}, pluck="title"),
                ["Credentials Test Source"],
            )


REST_ADMIN = "rest_connection_admin@test.com"
REST_USER = "rest_connection_user@test.com"
STORED_TOKEN = "stored-api-token"
STORED_URL = "https://api.example.com"
OTHER_URL = "https://elsewhere.example.com"


class TestRestConnectionTest(InsightsIntegrationTestCase):
    """A connection test sends the saved token, so the URL it goes to must be one
    the caller may set."""

    @classmethod
    def before_class(cls):
        create_user(REST_ADMIN, first_name="REST", last_name="Admin", roles="Insights Admin")
        create_user(REST_USER, first_name="REST", last_name="User", roles="Insights User")
        with patch("requests.Session.request"):
            cls.data_source = (
                frappe.get_doc(
                    {
                        "doctype": DT.DATA_SOURCE,
                        "title": "Credentials REST Source",
                        "type": "REST API",
                        "api_base_url": STORED_URL,
                        "api_authentication_type": "API Key / Bearer Token",
                        "api_token": STORED_TOKEN,
                    }
                )
                .insert()
                .name
            )

    @classmethod
    def after_class(cls):
        frappe.delete_doc(DT.DATA_SOURCE, cls.data_source, force=True, ignore_permissions=True)
        delete_users(REST_ADMIN, REST_USER)

    def before_test(self):
        # the method surface reads the request to check the HTTP verb
        set_request(method="POST", path="/api/method/insights.api.run_doc_method")

    def run_connection_test_as(self, user, refused=False, **fields):
        """Return the requests the test sent, as (url, authorization header)."""
        # the form sends the whole document, edits included
        doc = frappe.get_doc(DT.DATA_SOURCE, self.data_source).as_dict() | fields
        sent = []

        def request(session, method, url, **kwargs):
            sent.append((url, session.headers.get("Authorization")))
            return MagicMock(headers={"content-type": "application/json"}, json=lambda: {})

        with self.as_user(user), patch("requests.Session.request", request):
            if refused:
                with self.assertRaises(frappe.PermissionError):
                    run_doc_method("test_connection", doc)
            else:
                run_doc_method("test_connection", doc)
        return sent

    # @feature data-source.credentials-stay-with-admins
    def test_an_insights_user_cannot_test_the_source_against_another_url(self):
        sent = self.run_connection_test_as(REST_USER, refused=True, api_base_url=OTHER_URL, api_token="")
        self.assertEqual([request for request in sent if request[0].startswith(OTHER_URL)], [])

    # @feature data-source.credentials-stay-with-admins
    def test_an_insights_admin_tests_an_unsaved_edit_with_the_saved_token(self):
        sent = self.run_connection_test_as(REST_ADMIN, api_base_url=OTHER_URL, api_token="")
        self.assertEqual(sent, [(f"{OTHER_URL}/", f"Bearer {STORED_TOKEN}")])


class TestDuckDBHttpHeaders(unittest.TestCase):
    # @feature data-source.connect-duckdb
    def test_a_header_with_quotes_reaches_duckdb_as_one_header(self):
        """Unquoted, the key would not parse and the value would add an X-Other header."""
        source = frappe._dict(http_headers={"X-Team's-Key": "a', 'X-Other': 'b"})
        sql = get_http_secret(source, "Remote Source", "https://data.example.com/remote.duckdb")

        db = duckdb.connect()
        try:
            db.execute(sql)
            secrets = db.execute("select name, secret_string from duckdb_secrets()").fetchall()
        finally:
            db.close()

        self.assertEqual(len(secrets), 1)
        name, secret = secrets[0]
        self.assertEqual(name, "http_auth_remote_source")
        # DuckDB shows a quote inside a header as \'
        self.assertTrue(
            secret.endswith(r"extra_http_headers={'X-Team\'s-Key'='a\', \'X-Other\': \'b'}"), secret
        )
