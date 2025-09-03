# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import ibis


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
        ssl_mode="VERIFY_CA" if data_source.use_ssl else "DISABLED",
    )
