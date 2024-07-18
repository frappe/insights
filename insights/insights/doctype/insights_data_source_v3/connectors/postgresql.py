# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


def get_postgres_connection_string(data_source):
    extra_args = {"sslmode": "require" if data_source.use_ssl else "disable"}
    if data_source.connection_string:
        return data_source.connection_string, extra_args
    else:
        password = data_source.get_password(raise_exception=False)
        connection_string = (
            f"postgresql://{data_source.username}:{password}"
            f"@{data_source.host}:{data_source.port}/{data_source.database_name}"
        )
        return connection_string, extra_args
