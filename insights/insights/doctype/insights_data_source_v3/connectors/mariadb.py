# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
from urllib.parse import quote_plus

import ibis


def get_mariadb_connection_string(data_source):
    password = data_source.get_password(raise_exception=False)
    password = quote_plus(password) if password else ""
    connection_string = (
        f"mysql://{data_source.username}:{password}"
        f"@{data_source.host}:{data_source.port}/{data_source.database_name}"
        "?charset=utf8mb4&use_unicode=true"
    )
    if data_source.use_ssl:
        connection_string += "&ssl=true&ssl_verify_cert=true"
    return connection_string


def get_mariadb_connection(data_source):
    password = data_source.get_password(raise_exception=False)
    data_source.port = int(data_source.port or 3306)
    return ibis.mysql.connect(
        host=data_source.host,
        port=data_source.port,
        user=data_source.username,
        password=password,
        database=data_source.database_name,
        charset="utf8mb4",
        use_unicode=True,
        ssl="true" if data_source.use_ssl else None,
        ssl_verify_cert="true" if data_source.use_ssl else None,
    )
