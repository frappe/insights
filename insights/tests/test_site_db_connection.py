from unittest.mock import Mock, patch

import frappe
from frappe.tests import UnitTestCase

from insights.insights.doctype.insights_data_source_v3.connectors.frappe_db import (
    get_primary_data_source,
    get_replica_data_source,
    get_sitedb_connection,
)
from insights.insights.doctype.insights_data_source_v3.connectors.mariadb import (
    get_mariadb_connection,
)
from insights.tests.base import InsightsIntegrationTestCase

SOCKET = "/run/mysqld/mysqld.sock"


def socket_only_conf():
    conf = {"db_socket": SOCKET, "db_host": None, "db_port": None}
    return patch.dict(frappe.local.conf, conf)


class TestSiteDBSocket(UnitTestCase):
    # @feature data-source.site-db-socket
    def test_a_site_config_naming_only_a_socket_connects_the_site_db_over_it(self):
        with (
            socket_only_conf(),
            patch("MySQLdb.connect", return_value=Mock()) as connect,
            patch("ibis.mysql.from_connection"),
            patch("ibis.mysql.connect") as tcp_connect,
        ):
            get_mariadb_connection(get_primary_data_source())

        self.assertEqual(connect.call_args.kwargs["unix_socket"], SOCKET)
        self.assertNotIn("host", connect.call_args.kwargs)
        tcp_connect.assert_not_called()

    # @feature data-source.site-db-socket
    def test_a_replica_connects_over_tcp_past_the_primary_socket(self):
        for replica_conf in ({"replica_host": "replica.internal"}, {"replica_db_port": 3311}):
            with (
                self.subTest(**replica_conf),
                socket_only_conf(),
                patch.dict(frappe.local.conf, replica_conf),
            ):
                replica = get_replica_data_source()

            self.assertIsNone(replica.unix_socket)


def sitedb_connect_kwargs():
    captured = {}

    def record(**kwargs):
        captured.update(kwargs)
        return Mock()

    with (
        patch.dict(frappe.local.conf, {"db_socket": None}),
        patch("ibis.mysql.connect", side_effect=record),
    ):
        get_sitedb_connection()
    return captured


class TestSiteDBAsTheFramework(InsightsIntegrationTestCase):
    # @feature data-source.connect-mariadb
    def test_the_site_database_is_read_as_the_user_the_framework_connected_as(self):
        with patch.object(frappe.local.db, "user", "site_reader"):
            site = get_primary_data_source()

        self.assertEqual(site.username, "site_reader")
        self.assertEqual(site.database_name, frappe.local.db.cur_db_name)

    # @feature data-source.ssl
    def test_a_site_database_behind_ssl_is_read_with_the_frameworks_certificate(self):
        conf = {
            "db_ssl_ca": "/etc/ssl/db-ca.pem",
            "db_ssl_cert": "/etc/ssl/c.pem",
            "db_ssl_key": "/etc/ssl/k.pem",
        }
        with patch.dict(frappe.local.conf, conf):
            kwargs = sitedb_connect_kwargs()

        self.assertEqual(kwargs["ssl_mode"], "VERIFY_CA")
        self.assertEqual(
            kwargs["ssl"], {"ca": "/etc/ssl/db-ca.pem", "cert": "/etc/ssl/c.pem", "key": "/etc/ssl/k.pem"}
        )

    # @feature data-source.ssl
    def test_a_site_database_checks_the_hostname_only_when_the_framework_does(self):
        conf = {"db_ssl_ca": "/etc/ssl/db-ca.pem", "db_ssl_check_hostname": True}
        with patch.dict(frappe.local.conf, conf):
            kwargs = sitedb_connect_kwargs()

        self.assertEqual(kwargs["ssl_mode"], "VERIFY_IDENTITY")
