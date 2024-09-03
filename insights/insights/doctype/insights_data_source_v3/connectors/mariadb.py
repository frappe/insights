# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


def get_mariadb_connection_string(data_source):
    password = data_source.get_password(raise_exception=False)
    connection_string = (
        f"mysql://{data_source.username}:{password}"
        f"@{data_source.host}:{data_source.port}/{data_source.database_name}"
        "?charset=utf8mb4&use_unicode=true"
    )
    if data_source.use_ssl:
        connection_string += "&ssl=true&ssl_verify_cert=true"
    return connection_string
