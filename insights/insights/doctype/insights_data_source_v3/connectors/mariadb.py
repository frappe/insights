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
        connection_kwargs["unix_socket"] = socket
    else:
        connection_kwargs["host"] = data_source.host
        connection_kwargs["port"] = int(data_source.port or 3306)

    return ibis.mysql.connect(**connection_kwargs)
