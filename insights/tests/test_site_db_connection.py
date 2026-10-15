from unittest.mock import Mock, patch

import frappe
from frappe.tests import UnitTestCase

from insights.insights.doctype.insights_data_source_v3.connectors.frappe_db import (
    get_primary_data_source,
    get_replica_data_source,
)
from insights.insights.doctype.insights_data_source_v3.connectors.mariadb import (
    get_mariadb_connection,
)

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
