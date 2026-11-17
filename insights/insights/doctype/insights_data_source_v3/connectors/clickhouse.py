# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import ibis
from ibis.backends.sql.compilers.clickhouse import ClickHouseCompiler

from .compilers import StarExceptDropColumns


class InsightsClickHouseCompiler(StarExceptDropColumns, ClickHouseCompiler):
    pass


def get_clickhouse_connection(data_source):
    try:
        from ibis.backends.clickhouse import Backend as ClickHouseBackend  # noqa: F401
    except ImportError:
        raise ImportError("Please install the 'ibis-framework[clickhouse]' package to use ClickHouse.")

    password = data_source.get_password(raise_exception=False)
    data_source.port = int(data_source.port or 8123)

    db = ibis.clickhouse.connect(
        host=data_source.host,
        port=data_source.port,
        user=data_source.username,
        password=password,
        database=data_source.database_name,
        client_name="frappe_insights",
        secure=True if data_source.use_ssl else False,
        connect_timeout=5,
    )
    db.compiler = InsightsClickHouseCompiler()
    return db
