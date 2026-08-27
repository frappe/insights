# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import warnings
from functools import wraps

import ibis
import MySQLdb
from ibis.backends.mysql import Backend as MySQLBackend

from .ssl import ca_certificate_file


def suppress_ibis_utc_warning(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message="Unable to set session timezone",
            )
            return func(*args, **kwargs)

    return wrapper


@suppress_ibis_utc_warning
def get_mariadb_connection(data_source, socket=None):
    """
    Create an Ibis MariaDB/MySQL connection.

    Ibis 11 converts its default ``localhost`` host to ``127.0.0.1``.
    That forces TCP and prevents a supplied Unix socket from being used.

    For socket connections, establish the MySQLdb connection directly
    and then wrap that existing connection with the Ibis backend.
    """

    password = data_source.get_password(raise_exception=False)

    connection_kwargs = {
        "user": data_source.username,
        "password": password,
        "database": data_source.database_name,
        "charset": "utf8mb4",
        "use_unicode": True,
        "ssl_mode": "VERIFY_CA" if data_source.use_ssl else "DISABLED",
        "connect_timeout": 5,
    }

    if socket:
        raw_connection = MySQLdb.connect(
            host="localhost",
            unix_socket=socket,
            **connection_kwargs,
        )

        return MySQLBackend.from_connection(raw_connection)

    return ibis.mysql.connect(
        host=data_source.host or "127.0.0.1",
        port=int(data_source.port or 3306),
        **connection_kwargs,
    )
