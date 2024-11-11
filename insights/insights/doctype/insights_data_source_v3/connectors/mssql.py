# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
from urllib.parse import quote_plus


def get_mssql_connection_string(data_source):
    password = data_source.get_password(raise_exception=False)
    password = quote_plus(password) if password else ""
    connection_string = (
        f"mssql://{data_source.username}:{password}"
        f"@{data_source.host}:{data_source.port}/{data_source.database_name}"
        f"?driver={data_source.driver}"
    )
    if data_source.use_ssl:
        pass
    return connection_string
