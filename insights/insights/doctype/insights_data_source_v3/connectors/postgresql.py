# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from collections import Counter
from urllib.parse import parse_qsl, urlparse

import frappe
import ibis.expr.schema as sch
import sqlglot as sg
from ibis.backends.postgres import Backend as PostgresBackend

from .ssl import ca_certificate_file


class InsightsPostgresBackend(PostgresBackend):
    def _get_schema_using_query(self, query: str) -> sch.Schema:
        """The columns of native SQL, read off a zero-row run of it.

        ibis creates a temporary view over the query instead, which a read-only
        server such as a hot-standby replica refuses. This writes nothing.
        """
        subquery = sg.parse_one(query, read=self.dialect).subquery("_insights_columns")
        empty_result = sg.select("*").from_(subquery).limit(0).sql(self.dialect)

        con = self.con
        with con.cursor() as cursor, con.transaction():
            cursor.execute(empty_result)
            names = [column.name for column in cursor.description]
            if repeated := [name for name, count in Counter(names).items() if count > 1]:
                frappe.throw(
                    f"The query returns more than one column named {', '.join(repeated)}. "
                    "Give each column its own name with AS."
                )

            oids = [column.type_code for column in cursor.description]
            mods = [cursor.pgresult.fmod(i) for i in range(len(names))]
            # name types as `get_schema` does: format_type, and 'enum' for any enum
            type_names = cursor.execute(
                """\
SELECT CASE WHEN t.typtype = 'e' THEN 'enum' ELSE pg_catalog.format_type(c.oid, c.mod) END
FROM unnest(%(oids)s::oid[], %(mods)s::int4[]) WITH ORDINALITY AS c(oid, mod, position)
INNER JOIN pg_catalog.pg_type t ON t.oid = c.oid
ORDER BY c.position""",
                {"oids": oids, "mods": mods},
            ).fetchall()

        # a view's columns are never NOT NULL, so `get_schema` on the view said nullable too
        type_mapper = self.compiler.type_mapper
        return sch.Schema(
            {
                name: type_mapper.from_string(type_name, nullable=True)
                for name, (type_name,) in zip(names, type_names, strict=True)
            }
        )


def get_postgres_connection(data_source):
    if data_source.connection_string:
        url = urlparse(data_source.connection_string)
        return InsightsPostgresBackend()._from_url(url, **dict(parse_qsl(url.query)))

    password = data_source.get_password(raise_exception=False)
    data_source.port = int(data_source.port or 5432)

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

        return InsightsPostgresBackend().connect(
            host=data_source.host,
            port=data_source.port,
            user=data_source.username,
            password=password,
            database=data_source.database_name,
            schema=data_source.schema,
            connect_timeout=5,
            **ssl_options,
        )
