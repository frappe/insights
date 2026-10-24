# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import sqlglot as sg
import sqlglot.expressions as sge


class StarExceptDropColumns:
    """Compile a drop as `t.* EXCEPT (...)` for the compilers that drop by star.

    ibis 11 passes `except`, which sqlglot 30 renamed to `except_` and silently
    drops, so a drop compiled to `t.*` kept every column (ibis#11767).
    """

    def visit_DropColumns(self, op, *, parent, columns_to_drop):
        excludes = [sg.column(column, quoted=self.quoted) for column in columns_to_drop]
        star = sge.Star(except_=excludes)
        table = sg.to_identifier(parent.alias_or_name, quoted=self.quoted)
        return sg.select(sge.Column(this=star, table=table)).from_(parent)
