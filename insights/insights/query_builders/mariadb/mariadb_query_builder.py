# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from pypika import MySQLQuery
from ..pypika.helpers import ColumnProcessor, ExpressionProcessor
from ..pypika.pypika_query_builder import PypikaQueryBuilder


class MariaDBQueryBuilder(PypikaQueryBuilder):
    query_cls = MySQLQuery
    column_processor = ColumnProcessor
    expression_processor = ExpressionProcessor
