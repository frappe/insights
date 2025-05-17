# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from urllib.parse import quote_plus

import ibis


def get_postgres_connection(data_source):
    if data_source.connection_string:
        conn_string = quote_plus(data_source.connection_string)
        return ibis.connect(conn_string)
    else:
        password = data_source.get_password(raise_exception=False)
        data_source.port = int(data_source.port or 5432)
        return ibis.postgres.connect(
            host=data_source.host,
            port=data_source.port,
            user=data_source.username,
            password=password,
            database=data_source.database_name,
            schema=data_source.schema,
            sslmode="require" if data_source.use_ssl else None,
        )
