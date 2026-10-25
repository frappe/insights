# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import warnings
from functools import wraps

import ibis
import MySQLdb

from .ssl import ca_certificate_file


def suppress_ibis_utc_warning(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="Unable to set session timezone")
            return func(*args, **kwargs)

    return wrapper


@suppress_ibis_utc_warning
def get_mariadb_connection(data_source):
    password = data_source.get_password(raise_exception=False)
    data_source.port = int(data_source.port or 3306)

    with ca_certificate_file(data_source) as ca_certificate:
        if data_source.get("ssl_options"):
            ssl_options = data_source.ssl_options
        elif not data_source.use_ssl:
            ssl_options = {"ssl_mode": "DISABLED"}
        elif ca_certificate:
            # Measured against MariaDB Connector/C, which is what mysqlclient
            # links in an ordinary Frappe install: `ssl_mode` on its own
            # accepts a self-signed certificate, and a CA on its own is not
            # checked. Together they refuse one, so both are sent.
            ssl_options = {"ssl_mode": "VERIFY_IDENTITY", "ssl": {"ca": ca_certificate}}
        else:
            # It read VERIFY_CA before, which this driver cannot honour with no
            # CA to check against. Same connection, under a name that says so.
            ssl_options = {"ssl_mode": "REQUIRED"}

        connect_args = {
            "user": data_source.username,
            "password": password,
            "database": data_source.database_name,
            "charset": "utf8mb4",
            "use_unicode": True,
            "connect_timeout": 5,
            **ssl_options,
        }
        if data_source.get("unix_socket"):
            # ibis turns host "localhost" into 127.0.0.1, which forces TCP past the socket
            return ibis.mysql.from_connection(
                MySQLdb.connect(unix_socket=data_source.unix_socket, autocommit=True, **connect_args)
            )
        return ibis.mysql.connect(host=data_source.host, port=data_source.port, **connect_args)
