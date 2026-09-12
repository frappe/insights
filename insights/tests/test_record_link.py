"""Which result columns name a desk document, traced through the pipeline.

No chart and no dashboard: the trace reads operations and result columns, so
this is what it is given. What it needs from the site is the `Site DB` data
source and the doctypes it names.
"""

from insights.insights.doctype.insights_chart_v3.record_link import record_links
from insights.tests.base import InsightsIntegrationTestCase


def source(table_name="tabToDo"):
    return {
        "type": "source",
        "table": {"type": "table", "data_source": "Site DB", "table_name": table_name},
    }


def rename(column, new_name):
    return {"type": "rename", "column": {"type": "column", "column_name": column}, "new_name": new_name}


def mutate(new_name, expression):
    return {
        "type": "mutate",
        "new_name": new_name,
        "data_type": "String",
        "expression": {"type": "expression", "expression": expression},
    }


def summarize(*dimensions):
    return {
        "type": "summarize",
        "measures": [{"measure_name": "count", "column_name": "name", "aggregation": "count"}],
        "dimensions": [
            {"column_name": column, "dimension_name": shown, "data_type": "String"}
            for column, shown in dimensions
        ],
    }


def columns(*names):
    return [{"name": name, "type": "String"} for name in names]


def join(table_name, columns, on="name"):
    return {
        "type": "join",
        "join_type": "left",
        "table": {"type": "table", "data_source": "Site DB", "table_name": table_name},
        "join_condition": {
            "left_column": {"type": "column", "column_name": on},
            "right_column": {"type": "column", "column_name": "name"},
        },
        "select_columns": [{"type": "column", "column_name": column} for column in columns],
    }


class TestRecordLink(InsightsIntegrationTestCase):
    # the document a row is

    def test_a_doctype_table_names_its_own_records(self):
        links = record_links([source()], columns("name", "status"))
        self.assertEqual(links["name"], "ToDo")

    def test_the_link_follows_a_rename(self):
        # a rename says what the column is called, not what it holds
        operations = [source(), rename("name", "todo_id")]
        self.assertEqual(record_links(operations, columns("todo_id"))["todo_id"], "ToDo")

    def test_the_link_follows_a_copy(self):
        # the copy carries the document name too, so either column opens the record
        operations = [source(), mutate("todo_id", "name")]
        self.assertEqual(record_links(operations, columns("todo_id"))["todo_id"], "ToDo")

    def test_a_group_by_names_the_records_it_grouped_one_of(self):
        # the shape a Table chart runs: the summarize its config derives, naming
        # the column what the dimension asks for
        operations = [source(), summarize(("name", "Todo"))]
        self.assertEqual(record_links(operations, columns("Todo", "count"))["Todo"], "ToDo")

    def test_a_group_by_something_else_names_no_record(self):
        # one row per status is not one row per document
        operations = [source(), summarize(("status", "Status"))]
        self.assertEqual(record_links(operations, columns("Status", "count")), {})

    def test_a_dropped_name_names_no_record(self):
        operations = [source(), {"type": "select", "column_names": ["status", "priority"]}]
        self.assertEqual(record_links(operations, columns("status", "priority")), {})

    def test_a_name_written_over_names_no_record(self):
        # the cell holds an expression now, not a document name
        operations = [source(), mutate("name", "upper(status)")]
        self.assertEqual(record_links(operations, columns("name", "status")), {})

    def test_a_child_row_names_no_record_of_its_own(self):
        # a child row has no form: the desk routes the parent, which the row
        # cannot name. What the row points at still opens
        links = record_links([source("tabHas Role")], columns("name", "role"))
        self.assertEqual(links, {"role": "Role"})

    def test_a_union_names_no_record(self):
        # two tables, so a row cannot say which one it came from
        operations = [source(), {"type": "union", "table": {"type": "table", "table_name": "tabToDo"}}]
        self.assertEqual(record_links(operations, columns("name", "status")), {})

    # the documents a row points at

    def test_a_link_field_names_the_document_it_points_at(self):
        # `owner` on a ToDo is a Link to User, so the cell opens that user
        links = record_links([source()], columns("name", "owner", "description"))
        self.assertEqual(links, {"name": "ToDo", "owner": "User"})

    def test_a_column_that_is_no_field_of_the_table_names_nothing(self):
        links = record_links([source()], columns("made_up_column"))
        self.assertEqual(links, {})

    def test_a_field_that_is_not_a_link_names_nothing(self):
        # a status is a value, not an id
        self.assertEqual(record_links([source()], columns("status")), {})

    def test_a_joined_column_is_traced_to_the_table_it_came_from(self):
        # `language` is a Link on User and nothing on ToDo, so only a trace that
        # followed the join can say what it points at
        operations = [source(), join("tabUser", ["language"], on="owner")]
        links = record_links(operations, columns("name", "language"))
        self.assertEqual(links["language"], "Language")

    def test_a_join_to_a_table_says_what_the_joined_column_holds(self):
        # `owner == tabUser.name` says the column holds user ids, whatever the
        # left table calls the field
        operations = [source(), join("tabUser", ["language"], on="owner")]
        links = record_links(operations, columns("owner"))
        self.assertEqual(links["owner"], "User")

    def test_a_dynamic_link_is_followed_only_where_the_pipeline_pinned_it(self):
        # `reference_type` says what `reference_name` points at. Pinned to one
        # doctype, every row of the column is that doctype
        pinned = [
            source(),
            {
                "type": "filter",
                "column": {"type": "column", "column_name": "reference_type"},
                "operator": "=",
                "value": "ToDo",
            },
        ]
        links = record_links(pinned, columns("reference_name"))
        self.assertEqual(links["reference_name"], "ToDo")

    def test_an_unpinned_dynamic_link_names_nothing(self):
        # the column could hold a record of any doctype, and no cell says which
        self.assertEqual(record_links([source()], columns("reference_name")), {})

    def test_a_link_field_survives_a_group_by(self):
        operations = [source(), summarize(("owner", "Owner"))]
        self.assertEqual(record_links(operations, columns("Owner", "count"))["Owner"], "User")
