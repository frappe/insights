# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from pypika import SQLLiteQuery
from .helpers import SQLiteColumnProcessor, SQLiteExpressionProcessor
from ..pypika.pypika_query_builder import PypikaQueryBuilder


class SQLiteQueryBuilder(PypikaQueryBuilder):
    def __init__(self) -> None:
        self.query_cls = SQLLiteQuery
        self.column_processor = SQLiteColumnProcessor
        self.expression_processor = SQLiteExpressionProcessor
