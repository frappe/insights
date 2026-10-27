# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import warnings
from collections.abc import Iterator
from functools import wraps

import ibis
import MySQLdb
import MySQLdb.cursors
import pandas as pd
import pyarrow as pa
from ibis.backends.mysql import Backend as MySQLBackend
from ibis.backends.mysql.converter import MySQLPandasData
from ibis.expr.schema import Schema
from ibis.expr.types import Table

from .ssl import ca_certificate_file


def suppress_ibis_utc_warning(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="Unable to set session timezone")
            return func(*args, **kwargs)

    return wrapper


@suppress_ibis_utc_warning
def get_mariadb_connection(data_source):
    password = data_source.get_password(raise_exception=False)
    data_source.port = int(data_source.port or 3306)

    with ca_certificate_file(data_source) as ca_certificate:
        if not data_source.use_ssl:
            ssl_options = {"ssl_mode": "DISABLED"}
        elif ca_certificate:
            # Measured against MariaDB Connector/C, which is what mysqlclient
            # links in an ordinary Frappe install: `ssl_mode` on its own
            # accepts a self-signed certificate, and a CA on its own is not
            # checked. Together they refuse one, so both are sent.
            ssl_options = {"ssl_mode": "VERIFY_IDENTITY", "ssl": {"ca": ca_certificate}}
        else:
            # It read VERIFY_CA before, which this driver cannot honour with no
            # CA to check against. Same connection, under a name that says so.
            ssl_options = {"ssl_mode": "REQUIRED"}

        connect_args = {
            "user": data_source.username,
            "password": password,
            "database": data_source.database_name,
            "charset": "utf8mb4",
            "use_unicode": True,
            "connect_timeout": 5,
            **ssl_options,
        }
        if data_source.get("unix_socket"):
            # ibis turns host "localhost" into 127.0.0.1, which forces TCP past the socket
            return ibis.mysql.from_connection(
                MySQLdb.connect(unix_socket=data_source.unix_socket, autocommit=True, **connect_args)
            )
        return ibis.mysql.connect(host=data_source.host, port=data_source.port, **connect_args)


def read_pyarrow_batches(db: MySQLBackend, query: Table, chunk_size: int) -> pa.RecordBatchReader:
    """Read a query a chunk of rows at a time.

    ibis's own reader buffers the whole result in the client, then copies it
    into Python rows, pandas and Arrow at once. An unbuffered cursor holds only
    a chunk; each chunk is converted as ibis converts the whole result.
    """
    schema = query.schema()
    return pa.RecordBatchReader.from_batches(
        schema.to_pyarrow(), _fetch_chunks(db, query, schema, chunk_size)
    )


def _fetch_chunks(
    db: MySQLBackend, query: Table, schema: Schema, chunk_size: int
) -> Iterator[pa.RecordBatch]:
    arrow_schema = schema.to_pyarrow()
    db._run_pre_execute_hooks(query)
    with db.con.cursor(MySQLdb.cursors.SSCursor) as cursor:
        cursor.execute(db.compile(query))
        while rows := cursor.fetchmany(chunk_size):
            frame = pd.DataFrame.from_records(rows, columns=schema.names, coerce_float=True)
            frame = MySQLPandasData.convert_table(frame, schema)
            yield pa.RecordBatch.from_pandas(frame, schema=arrow_schema, preserve_index=False)
