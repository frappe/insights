# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from collections.abc import Callable
from urllib.parse import quote_plus

import frappe
import ibis
import ibis.expr.schema as sch
import sqlglot as sg
from ibis.backends.postgres import Backend as PostgresBackend

from .ssl import ca_certificate_file

EMPTY_RESULT_RELATION = "_insights_columns"


class InsightsPostgresBackend(PostgresBackend):
    """A Postgres backend that never writes to the server it reads rows from.

    ibis learns the columns of native SQL by creating a temporary view over it,
    which a hot-standby replica refuses. On a read replica the view is created on
    the primary instead, where it is planned but never run, and every row still
    comes from the replica. Without a primary, the columns come from a zero-row
    run of the query on this server.
    """

    connect_primary: Callable[[], PostgresBackend] | None = None
    _primary: PostgresBackend | None = None
    _primary_unreachable = False

    def _get_schema_using_query(self, query: str) -> sch.Schema:
        if primary := self._get_primary():
            return primary._get_schema_using_query(query)
        return self._get_schema_from_empty_result(query)

    def _get_primary(self) -> PostgresBackend | None:
        """The primary, opened on the first native SQL query and kept until disconnect."""
        if self._primary or self._primary_unreachable or not self.connect_primary:
            return self._primary
        try:
            self._primary = self.connect_primary()
        except Exception:
            # the replica can still answer, so the query runs; the outage is logged once
            self._primary_unreachable = True
            frappe.log_error(title="Insights: primary unreachable, reading columns on the replica")
        return self._primary

    def _get_schema_from_empty_result(self, query: str) -> sch.Schema:
        subquery = sg.parse_one(query, read=self.dialect).subquery(EMPTY_RESULT_RELATION)
        empty_result = sg.select("*").from_(subquery).limit(0).sql(self.dialect)

        con = self.con
        with con.cursor() as cursor, con.transaction():
            cursor.execute(empty_result)
            columns = cursor.description
            # name types as `get_schema` does: format_type, and 'enum' for any enum
            type_names = cursor.execute(
                """\
SELECT CASE WHEN t.typtype = 'e' THEN 'enum' ELSE pg_catalog.format_type(c.oid, c.mod) END
FROM unnest(%(oids)s::oid[], %(mods)s::int4[]) WITH ORDINALITY AS c(oid, mod, position)
INNER JOIN pg_catalog.pg_type t ON t.oid = c.oid
ORDER BY c.position""",
                {
                    "oids": [column.type_code for column in columns],
                    "mods": [column._fmod for column in columns],
                },
            ).fetchall()

        # a view's columns are always nullable, so the temporary view reports them that way too
        type_mapper = self.compiler.type_mapper
        return sch.Schema(
            {
                column.name: type_mapper.from_string(type_name, nullable=True)
                for column, (type_name,) in zip(columns, type_names, strict=True)
            }
        )

    def disconnect(self) -> None:
        if self._primary:
            self._primary.disconnect()
            self._primary = None
        super().disconnect()


def get_postgres_connection(data_source):
    db = _connect(data_source)
    if data_source.is_read_replica and not data_source.connection_string:
        db.connect_primary = lambda: get_primary_connection(data_source)
    return db


def get_primary_connection(data_source) -> PostgresBackend:
    """The primary of a read replica: its own host and login, the replica's database."""
    return _open(
        PostgresBackend(),
        data_source,
        host=data_source.primary_host,
        port=int(data_source.primary_port or 5432),
        user=data_source.primary_username,
        password=data_source.get_password("primary_password", raise_exception=False),
    )


def check_primary_connection(data_source):
    """Raise unless the primary's login can create the temporary view a query needs."""
    primary = get_primary_connection(data_source)
    try:
        primary._get_schema_using_query("SELECT 1 AS ok")
    finally:
        primary.disconnect()


def _connect(data_source):
    if data_source.connection_string:
        conn_string = quote_plus(data_source.connection_string)
        return ibis.connect(conn_string)

    data_source.port = int(data_source.port or 5432)
    return _open(
        InsightsPostgresBackend(),
        data_source,
        host=data_source.host,
        port=data_source.port,
        user=data_source.username,
        password=data_source.get_password(raise_exception=False),
    )


def _open(backend, data_source, host, port, user, password):
    with ca_certificate_file(data_source) as ca_certificate:
        ssl_options = {}
        if data_source.use_ssl:
            # "require" encrypts and accepts any certificate, so any host that
            # can answer for this one passes. A CA on the data source is how an
            # admin asks for more than that.
            ssl_options = (
                {"sslmode": "verify-full", "sslrootcert": ca_certificate}
                if ca_certificate
                else {"sslmode": "require"}
            )

        return backend.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=data_source.database_name,
            schema=data_source.schema,
            connect_timeout=5,
            **ssl_options,
        )
