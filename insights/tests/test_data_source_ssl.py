"""A data source can be verified, and says so by naming an authority.

Encryption on its own stops a listener and lets through anyone who can answer
for the database host. Which of the two a connection gets is decided by the CA
certificate on the data source: with one, the driver checks the server; without
one, it only encrypts. Peer tools read the same way, and every existing source
keeps the connection it already had.

The MariaDB pairing is measured, not assumed. Against MariaDB Connector/C, which
mysqlclient links in an ordinary Frappe install, `ssl_mode` alone accepts a
self-signed certificate and a CA alone is not checked. Sent together they refuse
one, so the test pins both.
"""

from typing import ClassVar
from unittest.mock import patch

from frappe.tests import UnitTestCase

from insights.insights.doctype.insights_data_source_v3.connectors.mariadb import (
    get_mariadb_connection,
)
from insights.insights.doctype.insights_data_source_v3.connectors.postgresql import (
    get_postgres_connection,
)

CA_CERTIFICATE = "-----BEGIN CERTIFICATE-----\nQ09SUE9SQVRFIENB\n-----END CERTIFICATE-----"


class FakeDataSource(dict):
    """Enough of a data source for a connector to read."""

    DEFAULTS: ClassVar[dict] = {
        "host": "db.internal",
        "port": 5432,
        "username": "svc",
        "database_name": "analytics",
        "schema": "",
        "connection_string": None,
        "use_ssl": 1,
        "ssl_ca": None,
    }

    def __init__(self, **fields):
        super().__init__(self.DEFAULTS | fields)

    def __getattr__(self, name):
        return self.get(name)

    def __setattr__(self, name, value):
        self[name] = value

    def get_password(self, raise_exception=False):
        return "secret"


def connect_kwargs(connector, backend, **fields):
    """The arguments the connector hands its driver.

    An authority is written out only for the length of the connect, so its
    contents are read while the driver would be reading them, under `anchor`.
    """
    captured = {}

    def record(**kwargs):
        captured.update(kwargs)
        anchor = kwargs.get("sslrootcert") or (kwargs.get("ssl") or {}).get("ca")
        if anchor:
            with open(anchor) as certificate:
                captured["anchor"] = certificate.read()

    with patch(backend, side_effect=record):
        connector(FakeDataSource(**fields))
    return captured


def postgres_kwargs(**fields):
    return connect_kwargs(get_postgres_connection, "ibis.postgres.connect", **fields)


def mariadb_kwargs(**fields):
    return connect_kwargs(get_mariadb_connection, "ibis.mysql.connect", **fields)


class TestPostgresSSL(UnitTestCase):
    def test_ssl_without_an_authority_only_encrypts(self):
        kwargs = postgres_kwargs()
        self.assertEqual(kwargs["sslmode"], "require")
        self.assertNotIn("sslrootcert", kwargs)

    def test_an_authority_turns_the_same_flag_into_verification(self):
        kwargs = postgres_kwargs(ssl_ca=CA_CERTIFICATE)
        self.assertEqual(kwargs["sslmode"], "verify-full")
        self.assertIn(CA_CERTIFICATE, kwargs["anchor"])

    def test_no_ssl_sends_no_ssl_options(self):
        kwargs = postgres_kwargs(use_ssl=0)
        self.assertNotIn("sslmode", kwargs)
        self.assertNotIn("sslrootcert", kwargs)


class TestMariaDBSSL(UnitTestCase):
    def test_ssl_without_an_authority_only_encrypts(self):
        kwargs = mariadb_kwargs()
        self.assertEqual(kwargs["ssl_mode"], "REQUIRED")
        self.assertNotIn("ssl", kwargs)

    def test_an_authority_sends_both_the_mode_and_the_certificate(self):
        kwargs = mariadb_kwargs(ssl_ca=CA_CERTIFICATE)
        self.assertEqual(kwargs["ssl_mode"], "VERIFY_IDENTITY")
        self.assertIn(CA_CERTIFICATE, kwargs["anchor"])

    def test_no_ssl_disables_it(self):
        kwargs = mariadb_kwargs(use_ssl=0)
        self.assertEqual(kwargs["ssl_mode"], "DISABLED")
        self.assertNotIn("ssl", kwargs)
