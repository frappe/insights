# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.database.mariadb.database import MariaDBDatabase
from frappe.model.document import Document


class DataSource(Document):
    def before_save(self):
        if self.test_connection():
            self.status = "Active"
        else:
            self.status = "Inactive"

    def create_db_instance(self):
        if hasattr(self, "db_instance") and self.db_instance:
            return

        if self.database_type != "MariaDB":
            raise NotImplementedError

        if self.database_type == "MariaDB":
            self.db_instance = MariaDBDatabase(
                host=self.host,
                port=self.port,
                user=self.username,
                password=self.get_password(),
            )

    @frappe.whitelist()
    def test_connection(self):
        self.create_db_instance()
        self.db_instance.connect()
        user_exists = self.db_instance.a_row_exists("User")
        self.db_instance.close()
        if user_exists:
            frappe.msgprint("Connection Successful", alert=True)
            return True

    @frappe.whitelist()
    def import_tables(self):
        tables = self.get_tables()
        table_links = self.get_foreign_key_constraints()

        for table in tables:
            if table_docname := frappe.db.get_value(
                "Table",
                {
                    "data_source": self.name,
                    "table": table.get("table"),
                },
                "name",
            ):
                doc = frappe.get_doc("Table", table_docname)
            else:
                doc = frappe.get_doc(
                    {
                        "doctype": "Table",
                        "data_source": self.name,
                        "table": table.get("table"),
                        "label": table.get("label"),
                    }
                )

            for table_link in table_links.get(table.get("label"), []):
                if not doc.get("table_links", table_link):
                    doc.append("table_links", table_link)

            doc.save()

    def get_foreign_key_constraints(self):
        # save Link Fields & Table Fields as ForeignKeyConstraints
        self.create_db_instance()
        self.db_instance.connect()

        DocField = frappe.qb.DocType("DocField")
        query = (
            frappe.qb.from_(DocField)
            .select(
                DocField.fieldname,
                DocField.fieldtype,
                DocField.options,
                DocField.parent,
            )
            .where((DocField.fieldtype == "Link") | (DocField.fieldtype == "Table"))
            .get_sql()
        )
        standard_links = self.db_instance.sql(query, as_dict=1)

        CustomField = frappe.qb.DocType("Custom Field")
        query = (
            frappe.qb.from_(CustomField)
            .select(
                CustomField.fieldname,
                CustomField.fieldtype,
                CustomField.options,
                CustomField.dt.as_("parent"),
            )
            .where(
                (CustomField.fieldtype == "Link") | (CustomField.fieldtype == "Table")
            )
            .get_sql()
        )
        custom_links = self.db_instance.sql(query, as_dict=1)

        dynamic_links = get_dynamic_link_map(self.db_instance)

        self.db_instance.close()

        links = standard_links + custom_links

        foreign_links = {}
        for link in links:
            if link.get("fieldtype") == "Link":
                foreign_links.setdefault(link.get("options"), []).append(
                    {
                        "foreign_key": link.get("fieldname"),
                        "foreign_table": "tab" + link.get("parent"),
                        "foreign_table_label": link.get("parent"),
                    }
                )
                foreign_links.setdefault(link.get("parent"), []).append(
                    {
                        "foreign_key": link.get("fieldname"),
                        "foreign_table": "tab" + link.get("options"),
                        "foreign_table_label": link.get("options"),
                    }
                )
            if link.get("fieldtype") == "Table":
                foreign_links.setdefault(link.get("parent"), []).append(
                    {
                        "foreign_key": "parent",
                        "foreign_table": "tab" + link.get("options"),
                        "foreign_table_label": link.get("options"),
                    }
                )
                foreign_links.setdefault(link.get("options"), []).append(
                    {
                        "foreign_key": "parent",
                        "foreign_table": "tab" + link.get("parent"),
                        "foreign_table_label": link.get("parent"),
                    }
                )

        for doctype in dynamic_links:
            if not doctype:
                continue

            for link in dynamic_links.get(doctype):
                foreign_links.setdefault(doctype, []).append(
                    {
                        "foreign_key": link.get("fieldname"),
                        "foreign_table": "tab" + link.get("parent"),
                        "foreign_table_label": link.get("parent"),
                    }
                )
                foreign_links.setdefault(link.get("parent"), []).append(
                    {
                        "foreign_key": link.get("fieldname"),
                        "foreign_table": "tab" + doctype,
                        "foreign_table_label": doctype,
                    }
                )

        return foreign_links

    def execute(self, query, debug=False):
        if not query:
            return

        self.create_db_instance()
        self.db_instance.connect()
        result = self.db_instance.sql(query, debug=debug)
        self.db_instance.close()

        return result

    def get_tables(self, tables=None):
        if not tables:
            tables = []

        self.create_db_instance()
        self.db_instance.connect()
        tables = self.db_instance.get_tables(cached=False)
        self.db_instance.close()

        # TODO: caching
        _tables = [
            {
                "table": table,
                "label": table.replace("tab", ""),
            }
            for table in list(tables)
        ]
        return _tables

    def get_columns(self, table):
        if not table:
            return []

        self.create_db_instance()
        self.db_instance.connect()
        columns = self.db_instance.sql(
            """
                select column_name, data_type
                from information_schema.columns
                where table_name = %s order by column_name
            """,
            table.get("table"),
            as_dict=1,
        )
        self.db_instance.close()

        # TODO: caching
        _columns = [
            {
                "table": table.get("table"),
                "column": d.get("column_name"),
                "table_label": table.get("label"),
                "type": d.get("data_type").title(),
                "label": frappe.unscrub(d.get("column_name")).rstrip().lstrip(),
            }
            for d in columns
        ]

        return _columns

    def get_distinct_column_values(self, column, search_text, limit=50):
        self.create_db_instance()
        self.db_instance.connect()

        Table = frappe.qb.Table(column.get("table"))
        Field = frappe.qb.Field(column.get("column"))
        query = (
            frappe.qb.from_(Table)
            .select(Field.as_("label"))
            .distinct()
            .select(Field.as_("value"))
            .where(Field.like(f"%{search_text}%"))
            .limit(limit)
            .get_sql()
        )

        values = self.db_instance.sql(query, as_dict=1)

        self.db_instance.close()

        # TODO: caching
        return values


def get_dynamic_link_map(db_instance):
    # copied from frappe.model.dynamic_links

    # Build from scratch
    dynamic_link_queries = [
        """select `tabDocField`.parent,
        `tabDocType`.read_only, `tabDocType`.in_create,
        `tabDocField`.fieldname, `tabDocField`.options
    from `tabDocField`, `tabDocType`
    where `tabDocField`.fieldtype='Dynamic Link' and
    `tabDocType`.`name`=`tabDocField`.parent
    order by `tabDocType`.read_only, `tabDocType`.in_create""",
        """select `tabCustom Field`.dt as parent,
        `tabDocType`.read_only, `tabDocType`.in_create,
        `tabCustom Field`.fieldname, `tabCustom Field`.options
    from `tabCustom Field`, `tabDocType`
    where `tabCustom Field`.fieldtype='Dynamic Link' and
    `tabDocType`.`name`=`tabCustom Field`.dt
    order by `tabDocType`.read_only, `tabDocType`.in_create""",
    ]

    dynamic_link_map = {}
    dynamic_links = []
    for query in dynamic_link_queries:
        dynamic_links += db_instance.sql(query, as_dict=True)

    for df in dynamic_links:
        meta = frappe.get_meta(df.parent)
        if meta.issingle:
            # always check in Single DocTypes
            dynamic_link_map.setdefault(meta.name, []).append(df)
        else:
            try:
                links = db_instance.sql_list(
                    """select distinct {options} from `tab{parent}`""".format(**df)
                )
                for doctype in links:
                    dynamic_link_map.setdefault(doctype, []).append(df)
            except frappe.db.TableMissingError:  # noqa: E722
                pass

    return dynamic_link_map
