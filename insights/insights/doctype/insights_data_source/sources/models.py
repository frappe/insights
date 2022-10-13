# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from typing import Protocol
from insights.insights.doctype.insights_query.insights_query import InsightsQuery


class Connection(Protocol):
    def get(self):
        ...

    def test(self) -> bool:
        ...

    def close(self) -> None:
        ...


class QueryBuilder(Protocol):
    def build(self, query: InsightsQuery):
        ...


class QueryRunner(Protocol):
    connection: Connection = None

    def execute(self):
        ...


class DataSourceImporter(Protocol):
    data_source: str = None
    connection: Connection = None
    query_runner: QueryRunner = None

    def import_data(self):
        ...


class BaseDataSource:
    def __init__(self):
        self.connection: Connection = None
        self.query_builder: QueryBuilder = None
        self.query_runner: QueryRunner = None
        self.data_importer: DataSourceImporter = None

    def test_connection(self):
        return self.connection.test()

    def build_query(self, query: InsightsQuery):
        return self.query_builder.build(query)

    def query(self, query, *args, **kwargs):
        return self.query_runner.execute(query, *args, **kwargs)

    def import_data(self, *args, **kwargs):
        return self.data_importer.import_data(*args, **kwargs)
