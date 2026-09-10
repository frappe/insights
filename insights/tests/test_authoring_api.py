import frappe

from insights.api.authoring import get_chart_data as get_authoring_data
from insights.api.authoring import get_drill_data as get_authoring_drill
from insights.api.authoring import get_drill_dimensions
from insights.insights.doctype.insights_data_source_v3.insights_data_source_v3 import db_connections
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import DT, as_user, create_user, delete_users, delete_workbooks

AUTHOR = "authoring_api_author@test.com"
# holds an Insights role, but none of the author's content
OUTSIDER = "authoring_api_outsider@test.com"
# holds no Insights role at all: a reader, not an author
READER = "authoring_api_reader@test.com"

WORKBOOK_TITLE = "Authoring API Test Workbook"
TODO_PREFIX = "Authoring API Test"
AUTHOR_TODOS = [f"{TODO_PREFIX} author 1", f"{TODO_PREFIX} author 2"]


def todo_operations():
    return [
        {
            "type": "source",
            "table": {"type": "table", "data_source": "Site DB", "table_name": "tabToDo"},
        },
        {
            "type": "filter",
            "column": {"type": "column", "column_name": "description"},
            "operator": "contains",
            "value": TODO_PREFIX,
        },
    ]


def counted(measure_name="count"):
    return {
        "measure_name": measure_name,
        "column_name": "name",
        "aggregation": "count",
        "data_type": "Integer",
    }


def grouped_by(column_name):
    return {"dimension_name": column_name, "column_name": column_name, "data_type": "String"}


def table_config(column_name="description"):
    """One row per value of `column_name`, counted."""
    return {
        "limit": 50,
        "rows": [grouped_by(column_name)],
        "columns": [],
        "values": [counted()],
        "order_by": [],
    }


def summarized_operations():
    """The pipeline a query builder is editing: the todos, counted by status.

    The other half of what an authoring surface can drill. It has no config to
    derive anything from — the summarize is written into the pipeline itself.
    """
    return [
        *todo_operations(),
        {"type": "summarize", "measures": [counted("Todos")], "dimensions": [grouped_by("status")]},
    ]


def rows_level(filters=None, measure=None):
    return {"segment_filters": filters or [], "action": {"rows": True, "measure": measure}}


def breakdown_level(dimension_name, filters=None, measure=None):
    return {
        "segment_filters": filters or [],
        "action": {"breakdown": dimension_name, "measure": measure},
    }


def equals(column, value):
    return {"column": column, "operator": "=", "value": value}


class TestAuthoringAPI(InsightsIntegrationTestCase):
    SAVEPOINT = "test_authoring_api"

    @classmethod
    def before_class(cls):
        cls.original_enable_permissions = frappe.db.get_single_value(DT.SETTINGS, "enable_permissions")
        frappe.db.set_single_value(DT.SETTINGS, "enable_permissions", 0)
        cls.cleanup()

        create_user(AUTHOR, first_name="Authoring", last_name="Author", roles="Insights User")
        create_user(OUTSIDER, first_name="Authoring", last_name="Outsider", roles="Insights User")
        create_user(READER, first_name="Authoring", last_name="Reader")

        for description in AUTHOR_TODOS:
            frappe.get_doc(
                {
                    "doctype": "ToDo",
                    "description": description,
                    "allocated_to": AUTHOR,
                    "assigned_by": "Administrator",
                }
            ).insert(ignore_permissions=True)

    @classmethod
    def after_class(cls):
        cls.cleanup()
        frappe.db.set_single_value(DT.SETTINGS, "enable_permissions", cls.original_enable_permissions)

    @classmethod
    def cleanup(cls):
        delete_workbooks(title_prefix=WORKBOOK_TITLE)
        for todo in frappe.get_all(
            "ToDo", filters={"description": ["like", f"%{TODO_PREFIX}%"]}, pluck="name"
        ):
            frappe.delete_doc("ToDo", todo, force=True, ignore_permissions=True)
        delete_users(AUTHOR, OUTSIDER, READER)

    # fixtures

    def make_content(self):
        """A saved chart the author owns, and the query behind it."""
        with as_user(AUTHOR):
            workbook = frappe.get_doc({"doctype": DT.WORKBOOK, "title": WORKBOOK_TITLE}).insert()
            query = frappe.get_doc(
                {
                    "doctype": DT.QUERY,
                    "title": "Authoring API Test Query",
                    "workbook": workbook.name,
                    "use_live_connection": 1,
                    "is_builder_query": 1,
                    "operations": todo_operations(),
                }
            ).insert()
            chart = frappe.get_doc(
                {
                    "doctype": DT.CHART,
                    "title": "Authoring API Test Chart",
                    "workbook": workbook.name,
                    "query": query.name,
                    "chart_type": "Table",
                    "config": table_config(),
                }
            ).insert()

        return frappe.get_doc(DT.QUERY, query.name), frappe.get_doc(DT.CHART, chart.name)

    def preview(self, user, **kwargs):
        with as_user(user), db_connections():
            return get_authoring_data(**kwargs)

    def drill(self, user, **kwargs):
        with as_user(user), db_connections():
            return get_authoring_drill(**kwargs)

    def candidates(self, user, **kwargs):
        with as_user(user), db_connections():
            return [d["name"] for d in get_drill_dimensions(**kwargs)["dimensions"]]

    # the preview

    def test_a_config_that_was_never_saved_draws_rows(self):
        query, _ = self.make_content()

        result = self.preview(
            AUTHOR,
            chart_type="Table",
            query=query.name,
            config=table_config(),
            force=True,
        )

        self.assertEqual(self.descriptions(result), sorted(AUTHOR_TODOS))
        self.assertEqual([column["name"] for column in result["columns"]], ["description", "count"])
        self.assertEqual(result["errors"], [])

    def test_the_preview_says_what_it_ran(self):
        query, _ = self.make_content()

        result = self.preview(AUTHOR, chart_type="Table", query=query.name, config=table_config())

        # the operations the drill-down forks, and the SQL the author debugs
        self.assertEqual(
            [operation["type"] for operation in result["operations"]],
            ["source", "summarize"],
        )
        self.assertEqual(result["operations"][0]["table"]["query_name"], query.name)
        self.assertIn("select", result["sql"].lower())

    def test_the_preview_runs_what_the_saved_chart_would(self):
        query, chart = self.make_content()

        result = self.preview(AUTHOR, chart_type="Table", query=query.name, config=table_config())

        # one deriver behind both doors, so what the author is shaping is what
        # every reader of the saved chart gets
        self.assertEqual(result["operations"], chart.get_operations())

    def test_a_half_configured_chart_says_what_is_missing(self):
        query, _ = self.make_content()
        config = table_config()
        config["rows"] = []

        result = self.preview(AUTHOR, chart_type="Table", query=query.name, config=config)

        # the builder's normal state on the way to a chart: no rows, and no error
        # either — the card keeps the last picture and says what is still needed
        self.assertEqual(result["errors"], ["Rows are required"])
        self.assertNotIn("rows", result)

    def test_the_grain_comes_back_with_the_rows(self):
        query, _ = self.make_content()
        config = table_config()
        config["rows"] = [
            {
                "column_name": "creation",
                "dimension_name": "creation",
                "data_type": "Datetime",
                "granularity": "month",
            }
        ]

        result = self.preview(AUTHOR, chart_type="Table", query=query.name, config=config)

        self.assertEqual(result["granularity"], {"creation": "month"})

    # dashboard filters, routed by the same function the viewer door uses

    def grid_items(self, chart: str, query: str, column: str = "description"):
        """A grid holding one chart card and one filter linked to it."""
        return [
            {"type": "chart", "chart": chart, "layout": {"i": "1", "x": 0, "y": 0, "w": 10, "h": 8}},
            {
                "type": "filter",
                "filter_name": "Description",
                "filter_type": "String",
                "links": {chart: f"`{query}`.`{column}`"},
                "layout": {"i": "2", "x": 0, "y": 0, "w": 4, "h": 1},
            },
        ]

    def test_the_grids_filters_reach_the_preview(self):
        query, chart = self.make_content()

        result = self.preview(
            AUTHOR,
            chart_type="Table",
            query=query.name,
            config=table_config(),
            chart_name=chart.name,
            dashboard_items=self.grid_items(chart.name, query.name),
            filters={"Description": {"operator": "contains", "value": "author 1"}},
            force=True,
        )

        # the builder sends the grid it is editing and nothing else: which query
        # the filter lands on is read off the links here, as it is for a reader
        self.assertEqual(self.descriptions(result), [AUTHOR_TODOS[0]])

    def test_a_filter_linked_to_another_card_leaves_this_one_alone(self):
        query, chart = self.make_content()
        items = self.grid_items(chart.name, query.name)
        items[1]["links"] = {"some-other-chart": f"`{query.name}`.`description`"}

        result = self.preview(
            AUTHOR,
            chart_type="Table",
            query=query.name,
            config=table_config(),
            chart_name=chart.name,
            dashboard_items=items,
            filters={"Description": {"operator": "contains", "value": "author 1"}},
            force=True,
        )

        # a link that names a card this preview is not drawing routes nowhere
        self.assertEqual(self.descriptions(result), sorted(AUTHOR_TODOS))

    # the drill, for a shape nobody has saved
    #
    # The walk itself is the viewer door's walk and is tested there. What is
    # tested here is only what differs: naming the shape instead of a chart, and
    # the pipeline that comes back with the rows.

    def test_a_config_that_was_never_saved_can_be_drilled(self):
        query, _ = self.make_content()

        result = self.drill(
            AUTHOR,
            query=query.name,
            chart_type="Table",
            config=table_config("status"),
            drill_stack=[rows_level([equals("status", "Open")], measure="count")],
        )

        # the segment of a card that exists nowhere but in the builder, as the
        # pipeline the caller runs for itself
        self.assertEqual(
            [operation["type"] for operation in result["operations"]],
            ["source", "filter_group"],
        )
        self.assertIn("description", [column["name"] for column in result["columns"]])

    def test_a_pipeline_that_belongs_to_no_chart_can_be_drilled(self):
        query, _ = self.make_content()

        result = self.drill(
            AUTHOR,
            query=query.name,
            operations=summarized_operations(),
            drill_stack=[rows_level([equals("status", "Open")], measure="Todos")],
        )

        # the query builder's own result table: there is no config to derive
        # anything from, so the pipeline it is editing is what it sends
        self.assertEqual(
            [operation["type"] for operation in result["operations"]],
            ["source", "filter", "filter_group"],
        )
        self.assertIn("description", [column["name"] for column in result["columns"]])

    def test_a_breakdown_of_an_unsaved_shape_groups_by_the_chosen_column(self):
        query, _ = self.make_content()

        result = self.drill(
            AUTHOR,
            query=query.name,
            operations=summarized_operations(),
            drill_stack=[breakdown_level("priority", [equals("status", "Open")], measure="Todos")],
        )

        self.assertEqual([column["name"] for column in result["columns"]], ["priority", "Todos"])
        self.assertEqual([(row["priority"], row["Todos"]) for row in result["rows"]], [("Medium", 2)])

    def test_a_breakdown_here_says_how_to_draw_it_too(self):
        query, _ = self.make_content()

        ordered = self.drill(
            AUTHOR,
            query=query.name,
            operations=summarized_operations(),
            drill_stack=[breakdown_level("creation", measure="Todos")],
        )
        ranked = self.drill(
            AUTHOR,
            query=query.name,
            operations=summarized_operations(),
            drill_stack=[breakdown_level("priority", measure="Todos")],
        )

        # the two fields the viewer door reports, on the door the builder uses:
        # one dialog draws both, so it must not have to know which fed it
        self.assertEqual((ordered["ordered"], ordered["granularity"]), (True, "minute"))
        self.assertEqual((ranked["ordered"], ranked["granularity"]), (False, None))

    def test_the_answer_carries_the_pipeline_the_level_opens_as(self):
        query, _ = self.make_content()

        result = self.drill(
            AUTHOR,
            query=query.name,
            chart_type="Table",
            config=table_config("status"),
            drill_stack=[rows_level([equals("status", "Open")], measure="count")],
        )

        # what "open as query" hands to the builder: the chart's pipeline cut
        # before the step that aggregated it, with the segment filtered in
        self.assertEqual(
            [operation["type"] for operation in result["operations"]],
            ["source", "filter_group"],
        )
        self.assertEqual(result["operations"][0]["table"]["query_name"], query.name)
        # and the connection it has to run on, which is the chart's
        self.assertTrue(result["use_live_connection"])

    def test_a_breakdown_opens_as_the_query_that_produced_its_ranking(self):
        query, _ = self.make_content()

        result = self.drill(
            AUTHOR,
            query=query.name,
            operations=summarized_operations(),
            drill_stack=[breakdown_level("priority", [equals("status", "Open")], measure="Todos")],
        )

        # the grouping and the sort the level is a picture of, not just the rows
        # underneath it: what opens is the query that drew what is on screen
        self.assertEqual(
            [operation["type"] for operation in result["operations"]],
            ["source", "filter", "filter_group", "summarize", "order_by"],
        )

    def test_a_rows_level_here_is_answered_with_its_pipeline_and_not_its_rows(self):
        query, _ = self.make_content()

        behind = self.drill(
            AUTHOR,
            query=query.name,
            operations=summarized_operations(),
            drill_stack=[rows_level([equals("status", "Open")], measure="Todos")],
        )

        # the caller loads the pipeline and runs it, so fetching the rows here
        # would be the same query run twice and drawn once
        self.assertEqual(behind["rows"], [])
        self.assertNotIn("total_row_count", behind)
        self.assertEqual(
            [operation["type"] for operation in behind["operations"]],
            ["source", "filter", "filter_group"],
        )
        # what the level answers in place of the rows: the shape they will have,
        # and which of their columns name a desk document
        self.assertIn("description", [column["name"] for column in behind["columns"]])
        self.assertEqual(behind["record_links"]["name"], "ToDo")

        breakdown = self.drill(
            AUTHOR,
            query=query.name,
            operations=summarized_operations(),
            drill_stack=[breakdown_level("priority", [equals("status", "Open")], measure="Todos")],
        )

        # a breakdown is a picture the dialog draws itself, so it still comes
        # back with its rows
        self.assertEqual([(row["priority"], row["Todos"]) for row in breakdown["rows"]], [("Medium", 2)])
        self.assertEqual(breakdown["total_row_count"], 1)

    def test_the_candidates_can_be_asked_for_on_their_own(self):
        query, _ = self.make_content()

        names = self.candidates(AUTHOR, query=query.name, operations=summarized_operations())

        # a chart's candidates ride its rows; a query builder fetches its rows
        # through its own document, so it has no such response to ride
        self.assertIn("status", names)
        self.assertIn("priority", names)
        self.assertIn("description", names)
        # the surface underneath the summarize, so what the summarize produced
        # is not on it, and neither is anything that measures rather than groups
        self.assertNotIn("Todos", names)
        self.assertNotIn("docstatus", names)

    def test_a_pipeline_that_aggregates_nothing_offers_no_candidates(self):
        query, _ = self.make_content()

        names = self.candidates(AUTHOR, query=query.name, operations=todo_operations())

        # asking what a raw result can be broken down by is a fair question even
        # when the answer is that it cannot
        self.assertEqual(names, [])

    def test_the_candidates_ride_the_previews_rows(self):
        query, _ = self.make_content()

        result = self.preview(AUTHOR, chart_type="Table", query=query.name, config=table_config())

        # the same field the viewer response carries, so a card reads its menu
        # off whichever feed drew it
        names = [dimension["name"] for dimension in result["drill"]["dimensions"]]
        self.assertIn("status", names)
        self.assertIn("priority", names)

    # the gate

    def test_a_reader_without_an_authoring_seat_is_refused(self):
        query, _ = self.make_content()
        self.assertNotIn("Insights User", frappe.get_roles(READER))

        with self.assertRaises(frappe.PermissionError):
            self.preview(READER, chart_type="Table", query=query.name, config=table_config())

    def test_a_query_the_caller_cannot_read_is_refused(self):
        query, _ = self.make_content()

        # naming a query is how this endpoint says what to run, so a seat alone is
        # not enough — the caller has to be able to read the query they name
        with self.assertRaises(frappe.PermissionError):
            self.preview(OUTSIDER, chart_type="Table", query=query.name, config=table_config())

    def test_a_reader_without_an_authoring_seat_cannot_drill(self):
        query, _ = self.make_content()

        # what this door adds is the pipeline, and the pipeline is the author's half
        with self.assertRaises(frappe.PermissionError):
            self.drill(
                READER,
                query=query.name,
                chart_type="Table",
                config=table_config("status"),
                drill_stack=[rows_level([equals("status", "Open")])],
            )

        with self.assertRaises(frappe.PermissionError):
            self.candidates(READER, query=query.name, operations=summarized_operations())

    def test_a_query_the_caller_cannot_read_cannot_be_drilled(self):
        query, _ = self.make_content()

        # naming a query is how this door says what to run, here as much as on
        # the preview — a seat is not a grant on someone else's content
        with self.assertRaises(frappe.PermissionError):
            self.drill(
                OUTSIDER,
                query=query.name,
                operations=summarized_operations(),
                drill_stack=[rows_level([equals("status", "Open")], measure="Todos")],
            )
