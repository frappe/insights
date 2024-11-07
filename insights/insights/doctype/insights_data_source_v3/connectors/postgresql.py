# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from urllib.parse import quote_plus


def get_postgres_connection_string(data_source):
    if data_source.connection_string:
        conn_string = quote_plus(data_source.connection_string)
        return conn_string
    else:
        password = data_source.get_password(raise_exception=False)
        password = quote_plus(password) if password else ""
        connection_string = (
            f"postgresql://{data_source.username}:{password}"
            f"@{data_source.host}:{data_source.port}/{data_source.database_name}"
        )
        if data_source.use_ssl:
            connection_string += "?sslmode=require"
        return connection_string
