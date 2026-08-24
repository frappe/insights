# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import MagicMock, patch

import frappe
from frappe import _dict
from frappe.tests.utils import FrappeTestCase

from insights.insights.doctype.insights_data_source_v3.connectors.frappe_db import (
    get_primary_data_source,
    get_sitedb_connection,
)
from insights.insights.doctype.insights_data_source_v3.connectors.mariadb import (
    get_mariadb_connection,
)


class TestInsightsDataSourcev3(FrappeTestCase):
    pass


class TestMariaDBSocketConnection(FrappeTestCase):
    """Layer 1: get_mariadb_connection() honors an explicit socket argument."""

    def _data_source(self, **overrides):
        base = _dict(
            username="_testuser",
            database_name="_testdb",
            use_ssl=False,
            host="127.0.0.1",
            port=3306,
        )
        base.update(overrides)
        base.get_password = MagicMock(return_value="secret")
        return base

    @patch("insights.insights.doctype.insights_data_source_v3.connectors.mariadb.ibis")
    def test_uses_unix_socket_when_configured(self, mock_ibis):
        data_source = self._data_source()

        get_mariadb_connection(data_source, socket="/tmp/mysql.sock")

        mock_ibis.mysql.connect.assert_called_once()
        _, kwargs = mock_ibis.mysql.connect.call_args
        self.assertEqual(kwargs.get("unix_socket"), "/tmp/mysql.sock")
        self.assertNotIn("host", kwargs)
        self.assertNotIn("port", kwargs)

    @patch("insights.insights.doctype.insights_data_source_v3.connectors.mariadb.ibis")
    def test_falls_back_to_host_and_port_without_socket(self, mock_ibis):
        data_source = self._data_source(host="127.0.0.1", port=3306)

        get_mariadb_connection(data_source, socket=None)

        mock_ibis.mysql.connect.assert_called_once()
        _, kwargs = mock_ibis.mysql.connect.call_args
        self.assertEqual(kwargs.get("host"), "127.0.0.1")
        self.assertEqual(kwargs.get("port"), 3306)
        self.assertNotIn("unix_socket", kwargs)


class TestSiteDBSocketWiring(FrappeTestCase):
    """Layer 2: frappe.conf.db_socket actually reaches the mariadb connector
    for the Site DB data source, end to end through get_sitedb_connection()."""

    def test_get_primary_data_source_does_not_carry_a_socket_field(self):
        # socket is connection metadata, not a persisted Data Source field --
        # get_primary_data_source() must not silently invent one.
        site_db = get_primary_data_source()
        self.assertNotIn("socket", site_db)

    @patch("insights.insights.doctype.insights_data_source_v3.connectors.mariadb.ibis")
    def test_sitedb_connection_passes_frappe_conf_db_socket(self, mock_ibis):
        with patch.object(frappe.conf, "db_socket", "/tmp/mysql.sock"):
            with patch.object(frappe.conf, "db_type", "mariadb"):
                get_sitedb_connection()

        mock_ibis.mysql.connect.assert_called_once()
        _, kwargs = mock_ibis.mysql.connect.call_args
        self.assertEqual(kwargs.get("unix_socket"), "/tmp/mysql.sock")

    @patch("insights.insights.doctype.insights_data_source_v3.connectors.mariadb.ibis")
    def test_sitedb_connection_uses_host_port_when_no_socket_configured(self, mock_ibis):
        with patch.object(frappe.conf, "db_socket", None):
            with patch.object(frappe.conf, "db_type", "mariadb"):
                get_sitedb_connection()

        mock_ibis.mysql.connect.assert_called_once()
        _, kwargs = mock_ibis.mysql.connect.call_args
        self.assertNotIn("unix_socket", kwargs)
        self.assertIn("host", kwargs)
        self.assertIn("port", kwargs)
