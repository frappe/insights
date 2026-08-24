# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import warnings
from functools import wraps

import ibis


def suppress_ibis_utc_warning(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="Unable to set session timezone")
            return func(*args, **kwargs)

    return wrapper


@suppress_ibis_utc_warning
def get_mariadb_connection(data_source, socket=None):
    password = data_source.get_password(raise_exception=False)
    connection_kwargs = dict(
        user=data_source.username,
        password=password,
        database=data_source.database_name,
        charset="utf8mb4",
        use_unicode=True,
        ssl_mode="VERIFY_CA" if data_source.use_ssl else "DISABLED",
        connect_timeout=5,
    )

    if socket:
        # When a Unix socket is configured, use it instead of TCP host/port.
        connection_kwargs["unix_socket"] = socket
    else:
        data_source.port = int(data_source.port or 3306)
        connection_kwargs["host"] = data_source.host
        connection_kwargs["port"] = data_source.port

    return ibis.mysql.connect(**connection_kwargs)
