# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from urllib.parse import quote_plus

import ibis
from ibis.backends.sql.compilers.postgres import PostgresCompiler

from .ssl import ca_certificate_file


class InsightsPostgresCompiler(PostgresCompiler):
    # PostgreSQL aborts on a zero divisor; MariaDB returns NULL
    def visit_Divide(self, op, *, left, right):
        return super().visit_Divide(op, left=left, right=self.f.nullif(right, 0))

    def visit_FloorDivide(self, op, *, left, right):
        return super().visit_FloorDivide(op, left=left, right=self.f.nullif(right, 0))

    def visit_Modulus(self, op, *, left, right):
        return super().visit_Modulus(op, left=left, right=self.f.nullif(right, 0))


def get_postgres_connection(data_source):
    db = connect(data_source)
    db.compiler = InsightsPostgresCompiler()
    return db


def connect(data_source):
    if data_source.connection_string:
        conn_string = quote_plus(data_source.connection_string)
        return ibis.connect(conn_string)

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

        return ibis.postgres.connect(
            host=data_source.host,
            port=data_source.port,
            user=data_source.username,
            password=password,
            database=data_source.database_name,
            schema=data_source.schema,
            connect_timeout=5,
            **ssl_options,
        )
