import json
from unittest.mock import patch

import frappe

from insights.api import run_doc_method
from insights.api.authoring import download_chart_rows as download_authoring_rows
from insights.api.authoring import download_drill_rows as download_authoring_drill_rows
from insights.api.authoring import get_chart_count as get_authoring_count
from insights.api.authoring import get_chart_data as get_authoring_data
from insights.api.authoring import get_drill_data as get_authoring_drill
from insights.api.authoring import get_drill_dimensions
from insights.api.authoring import get_drill_rows_values as get_authoring_drill_rows_values
from insights.api.view import get_chart
from insights.api.view import get_chart_data as get_view_data
from insights.api.workbooks import update_share_permissions
from insights.insights.doctype.insights_data_source_v3.insights_data_source_v3 import db_connections
from insights.not_permitted import NotPermitted
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import DT, as_user, create_user, delete_users, delete_workbooks
from insights.tests.test_run_as_owner import as_http_request

OWNER = "authoring_api_owner@test.com"
# holds an Insights role, but none of the owner's content
OUTSIDER = "authoring_api_outsider@test.com"
# admitted by the chart's visibility and holds no Insights role at all: a reader,
# not an owner
READER = "authoring_api_reader@test.com"

WORKBOOK_TITLE = "Authoring API Test Workbook"
TODO_PREFIX = "Authoring API Test"
OWNER_TODOS = [f"{TODO_PREFIX} owner 1", f"{TODO_PREFIX} owner 2"]


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

        create_user(OWNER, first_name="Authoring", last_name="Owner", roles="Insights User")
        create_user(OUTSIDER, first_name="Authoring", last_name="Outsider", roles="Insights User")
        create_user(READER, first_name="Authoring", last_name="Reader")

        for description in OWNER_TODOS:
            frappe.get_doc(
                {
                    "doctype": "ToDo",
                    "description": description,
                    "allocated_to": OWNER,
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
        delete_users(OWNER, OUTSIDER, READER)

    def make_content(self):
        """A saved chart the owner owns, and the query behind it."""
        with as_user(OWNER):
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
                    # the owner's own rows, so a reader sees the same numbers
                    "run_as_owner": 1,
                    "visibility": "Everyone",
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

    # @feature charts.preview
    def test_a_config_that_was_never_saved_draws_rows(self):
        query, _ = self.make_content()

        result = self.preview(
            OWNER,
            chart_type="Table",
            query=query.name,
            config=table_config(),
            force=True,
        )

        self.assertEqual(self.descriptions(result), sorted(OWNER_TODOS))
        self.assertEqual([column["name"] for column in result["columns"]], ["description", "count"])
        self.assertEqual(result["errors"], [])

    # @feature charts.preview charts.view-sql
    def test_the_preview_says_what_it_ran(self):
        query, _ = self.make_content()

        result = self.preview(OWNER, chart_type="Table", query=query.name, config=table_config())

        # the operations the drill-down forks, and the SQL the owner debugs
        self.assertEqual(
            [operation["type"] for operation in result["operations"]],
            ["source", "summarize"],
        )
        self.assertEqual(result["operations"][0]["table"]["query_name"], query.name)
        self.assertIn("select", result["sql"].lower())

    # @feature charts.preview
    def test_the_preview_runs_what_the_saved_chart_would(self):
        query, chart = self.make_content()

        result = self.preview(OWNER, chart_type="Table", query=query.name, config=table_config())

        # one deriver behind both endpoints, so what the owner is shaping is what
        # every reader of the saved chart gets
        self.assertEqual(result["operations"], chart.get_operations())

    # @feature charts.missing-slot-message
    def test_a_half_configured_chart_says_what_is_missing(self):
        query, _ = self.make_content()
        config = table_config()
        config["rows"] = []

        result = self.preview(OWNER, chart_type="Table", query=query.name, config=config)

        # the builder's normal state on the way to a chart: no rows, and no error
        # either — the card keeps the last picture and says what is still needed
        self.assertEqual(result["errors"], ["Rows are required"])
        self.assertNotIn("rows", result)

    # @feature charts.missing-slot-message
    def test_a_half_configured_chart_says_what_is_missing_to_a_reader_too(self):
        """`chart_preview.ts` in a builder a read-only collaborator opened, over
        a saved chart missing a slot. They are answered as the view answers its
        reader, and a writer is told what is missing: so are they, whatever the
        chart runs as."""
        query, chart = self.make_content()
        self.share_workbook(chart, write=0)
        config = table_config()
        config["rows"] = []
        chart.db_set("config", frappe.as_json(config), update_modified=False)

        for run_as_owner in (1, 0):
            chart.db_set("run_as_owner", run_as_owner, update_modified=False)
            result = self.preview(
                OUTSIDER, chart_type="Table", query=query.name, config=config, chart_name=chart.name
            )

            self.assertEqual(result["errors"], ["Rows are required"], run_as_owner)
            self.assertNotIn("rows", result, run_as_owner)

    # @feature charts.preview
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

        result = self.preview(OWNER, chart_type="Table", query=query.name, config=config)

        self.assertEqual(result["granularity"], {"creation": "month"})

    # @feature charts.preview
    def test_a_saved_chart_answers_with_the_grain_and_the_links_too(self):
        """A share link reads `view.get_chart_data`, never this endpoint.
        Without the grain a table grouped by month prints `2024-01-01` where the
        builder shows `Jan 2024`, and without the links its ids draw nothing."""
        _, chart = self.make_content()
        config = table_config()
        config["rows"] = [
            {
                "column_name": "creation",
                "dimension_name": "creation",
                "data_type": "Datetime",
                "granularity": "month",
            },
            grouped_by("name"),
        ]
        with as_user(OWNER):
            chart.config = config
            chart.save()

        with as_user(OWNER), db_connections():
            result = get_view_data(chart.name, force=True)

        self.assertEqual(result["granularity"], {"creation": "month"})
        self.assertEqual(result["record_links"], {"name": "ToDo"})

    def allow_download(self, max_export_rows=0):
        for field in ("allow_download", "max_export_rows"):
            original = frappe.db.get_single_value(DT.SETTINGS, field)
            self.addCleanup(frappe.db.set_single_value, DT.SETTINGS, field, original)
        frappe.db.set_single_value(DT.SETTINGS, "allow_download", 1)
        frappe.db.set_single_value(DT.SETTINGS, "max_export_rows", max_export_rows)

    # @feature charts.table-pager
    def test_the_count_covers_the_pages_the_rows_are_cut_into(self):
        """`authoring.get_chart_count`, which the builder's table card calls."""
        query, chart = self.make_content()
        shape = {"chart_type": "Table", "query": query.name, "config": table_config()}

        page = self.preview(OWNER, page_size=1, **shape)
        with as_user(OWNER), db_connections():
            preview_count = get_authoring_count(**shape)
            saved_count = get_authoring_count(chart_name=chart.name, **shape)

        self.assertEqual(len(page["rows"]), 1)
        self.assertEqual((preview_count, saved_count), (len(OWNER_TODOS), len(OWNER_TODOS)))

    # @feature charts.export-rows
    def test_a_download_is_the_charts_own_rows_up_to_the_export_limit(self):
        """`authoring.download_chart_rows`, which the builder's table card calls."""
        query, chart = self.make_content()
        shape = {"chart_type": "Table", "query": query.name, "config": table_config()}
        self.allow_download()

        def lines(csv):
            return csv.strip().splitlines()

        with as_user(OWNER), db_connections():
            preview_csv = download_authoring_rows(**shape)
            saved_csv = download_authoring_rows(chart_name=chart.name, **shape)
            frappe.db.set_single_value(DT.SETTINGS, "max_export_rows", 1)
            limited_csv = download_authoring_rows(chart_name=chart.name, **shape)

        # the chart's summarized rows, not the todos its query reads
        self.assertEqual(lines(preview_csv), lines(saved_csv))
        self.assertEqual(lines(saved_csv)[0], "description,count")
        self.assertEqual(len(lines(saved_csv)), 1 + len(OWNER_TODOS))
        self.assertEqual(len(lines(limited_csv)), 2)

    # @feature charts.table-pager charts.export-rows permissions.chart-run-as-owner
    def test_a_caller_who_may_not_write_the_chart_keeps_its_one_page(self):
        """The authoring doors hand a caller who is not the author to the view,
        which answers a picture-only reader with the chart's one page."""
        query, chart = self.make_content()
        shape = {
            "chart_type": "Table",
            "query": query.name,
            "config": table_config(),
            "chart_name": chart.name,
        }
        self.allow_download()

        first = self.preview(OUTSIDER, force=True, **shape)
        second = self.preview(OUTSIDER, page=2, force=True, **shape)
        with as_user(OUTSIDER), db_connections():
            with self.assertRaises(NotPermitted):
                get_authoring_count(**shape)
            with self.assertRaises(frappe.PermissionError):
                download_authoring_rows(**shape)

        self.assertFalse(first["can_read_rows"])
        self.assertEqual(second["rows"], first["rows"])

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

    # @feature dashboard.filter-links
    def test_the_grids_filters_reach_the_preview(self):
        query, chart = self.make_content()

        result = self.preview(
            OWNER,
            chart_type="Table",
            query=query.name,
            config=table_config(),
            chart_name=chart.name,
            dashboard_items=self.grid_items(chart.name, query.name),
            filters={"Description": {"operator": "contains", "value": "owner 1"}},
            force=True,
        )

        # the builder sends the grid it is editing and nothing else: which query
        # the filter lands on is read off the links here, as it is for a reader
        self.assertEqual(self.descriptions(result), [OWNER_TODOS[0]])

    # @feature dashboard.filter-links
    def test_a_filter_linked_to_another_card_leaves_this_one_alone(self):
        query, chart = self.make_content()
        items = self.grid_items(chart.name, query.name)
        items[1]["links"] = {"some-other-chart": f"`{query.name}`.`description`"}

        result = self.preview(
            OWNER,
            chart_type="Table",
            query=query.name,
            config=table_config(),
            chart_name=chart.name,
            dashboard_items=items,
            filters={"Description": {"operator": "contains", "value": "owner 1"}},
            force=True,
        )

        # a link that names a card this preview is not drawing routes nowhere
        self.assertEqual(self.descriptions(result), sorted(OWNER_TODOS))

    # The walk itself is `insights.api.view`'s walk and is tested there. What is
    # tested here is only what differs: naming the shape instead of a chart, and
    # the pipeline that comes back with the rows.

    # @feature charts.drill-rows
    def test_a_config_that_was_never_saved_can_be_drilled(self):
        query, _ = self.make_content()

        result = self.drill(
            OWNER,
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

    # @feature charts.drill-rows
    def test_a_pipeline_that_belongs_to_no_chart_can_be_drilled(self):
        query, _ = self.make_content()

        result = self.drill(
            OWNER,
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

    # @feature charts.drill-breakdown
    def test_a_breakdown_of_an_unsaved_shape_groups_by_the_chosen_column(self):
        query, _ = self.make_content()

        result = self.drill(
            OWNER,
            query=query.name,
            operations=summarized_operations(),
            drill_stack=[breakdown_level("priority", [equals("status", "Open")], measure="Todos")],
        )

        self.assertEqual([column["name"] for column in result["columns"]], ["priority", "Todos"])
        self.assertEqual([(row["priority"], row["Todos"]) for row in result["rows"]], [("Medium", 2)])

    # @feature charts.drill-breakdown-shape
    def test_a_breakdown_here_says_how_to_draw_it_too(self):
        query, _ = self.make_content()

        ordered = self.drill(
            OWNER,
            query=query.name,
            operations=summarized_operations(),
            drill_stack=[breakdown_level("creation", measure="Todos")],
        )
        ranked = self.drill(
            OWNER,
            query=query.name,
            operations=summarized_operations(),
            drill_stack=[breakdown_level("priority", measure="Todos")],
        )

        # the two fields `insights.api.view` reports, on the endpoint the builder uses:
        # one dialog draws both, so it must not have to know which fed it
        self.assertEqual((ordered["ordered"], ordered["granularity"]), (True, "minute"))
        self.assertEqual((ranked["ordered"], ranked["granularity"]), (False, None))

    # @feature charts.drill-open-as-query
    def test_the_answer_carries_the_pipeline_the_level_opens_as(self):
        query, _ = self.make_content()

        result = self.drill(
            OWNER,
            query=query.name,
            chart_type="Table",
            config=table_config("status"),
            drill_stack=[rows_level([equals("status", "Open")], measure="count")],
        )

        # what "open as query" hands to the builder: the chart's pipeline cut
        # before the operation that aggregated it, with the segment filtered in
        self.assertEqual(
            [operation["type"] for operation in result["operations"]],
            ["source", "filter_group"],
        )
        self.assertEqual(result["operations"][0]["table"]["query_name"], query.name)
        # and the connection it has to run on, which is the chart's
        self.assertTrue(result["use_live_connection"])

    # @feature charts.drill-open-as-query
    def test_a_breakdown_opens_as_the_query_that_produced_its_ranking(self):
        query, _ = self.make_content()

        result = self.drill(
            OWNER,
            query=query.name,
            operations=summarized_operations(),
            drill_stack=[breakdown_level("priority", [equals("status", "Open")], measure="Todos")],
        )

        # the grouping and the sort the level is a picture of, not just the rows
        # underneath it: what opens is the query that drew what is on screen,
        # ties included
        self.assertEqual(
            [operation["type"] for operation in result["operations"]],
            ["source", "filter", "filter_group", "summarize", "order_by", "order_by"],
        )

    # @feature charts.drill-rows charts.drill-open-as-query
    def test_a_rows_level_here_is_read_here_and_carries_the_pipeline_it_opens_as(self):
        """`AuthoringDrillDown.vue` draws the rows the server read, and "open as
        query" adds the pipeline beside them to the workbook. Run anywhere else,
        the pipeline reads as its caller."""
        query, _ = self.make_content()

        behind = self.drill(
            OWNER,
            query=query.name,
            operations=summarized_operations(),
            drill_stack=[rows_level([equals("status", "Open")], measure="Todos")],
        )

        self.assertEqual(self.descriptions(behind), sorted(OWNER_TODOS))
        self.assertEqual(behind["total_row_count"], len(OWNER_TODOS))
        self.assertEqual(behind["record_links"]["name"], "ToDo")
        self.assertEqual(
            [operation["type"] for operation in behind["operations"]],
            ["source", "filter", "filter_group"],
        )

        breakdown = self.drill(
            OWNER,
            query=query.name,
            operations=summarized_operations(),
            drill_stack=[breakdown_level("priority", [equals("status", "Open")], measure="Todos")],
        )

        self.assertEqual([(row["priority"], row["Todos"]) for row in breakdown["rows"]], [("Medium", 2)])
        self.assertEqual(breakdown["total_row_count"], 1)

    # @feature charts.drill-breakdown-offers
    def test_the_candidates_can_be_asked_for_on_their_own(self):
        query, _ = self.make_content()

        names = self.candidates(OWNER, query=query.name, operations=summarized_operations())

        # a chart's candidates come back with its rows. A query builder fetches its
        # rows through its own document, so it has no such response
        self.assertIn("status", names)
        self.assertIn("priority", names)
        self.assertIn("description", names)
        # the surface underneath the summarize, so what the summarize produced
        # is not on it, and neither is anything that measures rather than groups
        self.assertNotIn("Todos", names)
        self.assertNotIn("docstatus", names)

    # @feature charts.drill-breakdown-offers
    def test_a_pipeline_that_aggregates_nothing_offers_no_candidates(self):
        query, _ = self.make_content()

        names = self.candidates(OWNER, query=query.name, operations=todo_operations())

        # asking what a raw result can be broken down by is a fair question even
        # when the answer is that it cannot
        self.assertEqual(names, [])

    # @feature charts.drill-breakdown-offers
    def test_the_candidates_ride_the_previews_rows(self):
        query, _ = self.make_content()

        result = self.preview(OWNER, chart_type="Table", query=query.name, config=table_config())

        # the same field the viewer response carries, so a card reads its menu
        # off whichever feed drew it
        names = [dimension["name"] for dimension in result["drill"]["dimensions"]]
        self.assertIn("status", names)
        self.assertIn("priority", names)

    # the gate

    # @feature permissions.authoring-needs-role
    def test_a_reader_without_an_insights_role_is_refused(self):
        query, chart = self.make_content()
        self.assertNotIn("Insights User", frappe.get_roles(READER))

        # the reader may see the chart — it is the derivation behind it they may not
        with as_user(READER):
            self.assertEqual(get_chart(chart=chart.name)["name"], chart.name)

        with self.assertRaises(frappe.PermissionError):
            self.preview(READER, chart_type="Table", query=query.name, config=table_config())

    # @feature permissions.authoring-needs-role
    def test_a_query_the_caller_cannot_read_is_refused(self):
        query, chart = self.make_content()
        # naming a query is how this endpoint says what to run, so the role alone
        # is not enough — the caller has to be able to read the query they name
        chart.db_set("visibility", "Private", update_modified=False)

        with self.assertRaises(frappe.PermissionError):
            self.preview(OUTSIDER, chart_type="Table", query=query.name, config=table_config())

    # @feature permissions.authoring-needs-role
    def test_a_reader_without_an_insights_role_cannot_drill(self):
        query, _ = self.make_content()

        # the reader may drill the saved chart through `insights.api.view` all
        # day. What these endpoints add is the pipeline, the owner's half
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

    # @feature permissions.authoring-needs-role
    def test_a_query_the_caller_cannot_read_cannot_be_drilled(self):
        query, chart = self.make_content()
        chart.db_set("visibility", "Private", update_modified=False)

        # naming a query is how these endpoints say what to run, here as much as
        # on the preview — a role is not a grant on someone else's content
        with self.assertRaises(frappe.PermissionError):
            self.drill(
                OUTSIDER,
                query=query.name,
                operations=summarized_operations(),
                drill_stack=[rows_level([equals("status", "Open")], measure="Todos")],
            )

    # @feature permissions.authoring-needs-role
    def test_a_document_the_caller_cannot_read_cannot_name_the_preview(self):
        query, chart = self.make_content()
        chart.db_set("visibility", "Private", update_modified=False)

        with as_user(OUTSIDER):
            workbook = frappe.get_doc(
                {"doctype": DT.WORKBOOK, "title": f"{WORKBOOK_TITLE} Outsider"}
            ).insert()
            own = frappe.get_doc(
                {
                    "doctype": DT.QUERY,
                    "title": "Outsider Query",
                    "workbook": workbook.name,
                    "use_live_connection": 1,
                    "is_builder_query": 1,
                    "operations": todo_operations(),
                }
            ).insert()

        # the name a preview runs under tells the engine which queries the
        # execution is already authorized for, so a name someone else's
        # document holds is refused — whichever document holds it. A chart the
        # caller may not write answers as the view does, with Not Found
        for name, refusal in ((chart.name, frappe.DoesNotExistError), (query.name, frappe.PermissionError)):
            with self.assertRaises(refusal):
                self.preview(
                    OUTSIDER,
                    chart_type="Table",
                    query=own.name,
                    config=table_config(),
                    chart_name=name,
                )

    def make_filtered_content(self):
        """The owner's chart, narrowed by its own config to one of the owner's todos."""
        query, chart = self.make_content()
        config = frappe.parse_json(chart.config)
        config["filters"] = {
            "filters": [
                {
                    "column": {"type": "column", "column_name": "description"},
                    "operator": "=",
                    "value": OWNER_TODOS[0],
                }
            ],
            "logical_operator": "And",
        }
        chart.db_set("config", frappe.as_json(config), update_modified=False)
        return query, frappe.get_doc(DT.CHART, chart.name)

    def share_workbook(self, chart, write):
        with as_user(OWNER):
            update_share_permissions(chart.workbook, [{"user": OUTSIDER, "read": 1, "write": write}])

    # @feature permissions.request-body-not-trusted permissions.chart-run-as-owner
    def test_a_reader_who_cannot_edit_the_chart_draws_the_stored_chart(self):
        """`chart_preview.ts` sends `chart_name` with the config it holds, and a
        view response strips `filters` from that config (`present_config`), so a
        reader who may open the chart but not edit it sends it without them. The
        stored chart answers: a config the caller wrote is not the chart's, and
        naming the chart must not run it with the owner's access."""
        query, chart = self.make_filtered_content()
        self.assertTrue(chart.run_as_owner)
        self.share_workbook(chart, write=0)

        with as_user(OUTSIDER):
            self.assertTrue(frappe.has_permission(DT.CHART, ptype="read", doc=chart.name))
            self.assertFalse(frappe.has_permission(DT.CHART, ptype="write", doc=chart.name))

        with as_user(OUTSIDER), db_connections():
            card = get_view_data(chart.name, force=True)

        reshaped = self.preview(
            OUTSIDER,
            chart_type="Table",
            query=query.name,
            config=table_config(),
            chart_name=chart.name,
            force=True,
        )

        self.assertEqual(self.descriptions(card), [OWNER_TODOS[0]])
        self.assertEqual(self.descriptions(reshaped), self.descriptions(card))

    # @feature permissions.request-body-not-trusted permissions.chart-run-as-owner
    def test_a_reader_who_cannot_edit_the_chart_gets_its_picture_and_nothing_behind_it(self):
        """`chart_preview.ts` in a builder a read-only collaborator opened sends
        the grid it holds, a page window and `chart_name`. They get what
        `view.get_chart_data` gives its reader, whatever the chart runs as: the
        stored chart at its own `limit`, routed by no link of theirs, no SQL or
        pipeline, and the chart the rows answer."""
        query, chart = self.make_content()
        self.share_workbook(chart, write=0)

        for run_as_owner, todos in ((1, sorted(OWNER_TODOS)), (0, [])):
            chart.db_set("run_as_owner", run_as_owner, update_modified=False)
            answer = self.preview(
                OUTSIDER,
                chart_type="Table",
                query=query.name,
                config=table_config(),
                chart_name=chart.name,
                dashboard_items=self.grid_items(chart.name, query.name),
                filters={"Description": {"operator": "contains", "value": "owner 1"}},
                page=2,
                page_size=1,
                force=True,
            )

            self.assertEqual(self.descriptions(answer), todos, run_as_owner)
            for key in ("sql", "operations"):
                self.assertNotIn(key, answer, run_as_owner)
            self.assertEqual(answer["chart"]["name"], chart.name, run_as_owner)
            self.assertNotIn("filters", answer["chart"]["config"], run_as_owner)

    # @feature permissions.request-body-not-trusted charts.drill-open-as-query
    def test_a_reader_who_cannot_edit_the_chart_gets_no_pipeline_from_its_drill(self):
        """`AuthoringDrillDown.vue` offers "open as query" where a level carries
        the pipeline it was cut as. A read-only collaborator of a chart run as
        its reader drills it as `view.get_drill_data` would drill it for them;
        a collaborator who may edit it gets the pipeline."""
        query, chart = self.make_content()
        chart.db_set("run_as_owner", 0, update_modified=False)
        shape = {
            "query": query.name,
            "chart_type": "Table",
            "config": table_config(),
            "chart_name": chart.name,
        }

        for write in (0, 1):
            self.share_workbook(chart, write=write)
            for level in (rows_level(), breakdown_level("status")):
                answer = self.drill(OUTSIDER, drill_stack=[level], **shape)
                self.assertNotIn("not_permitted", answer, (write, level))
                self.assertEqual("operations" in answer, bool(write), (write, level))

    # @feature dashboard.filter-links permissions.chart-run-as-owner
    def test_a_reader_who_cannot_edit_the_chart_is_routed_by_the_saved_dashboard(self):
        """`chart_preview.ts` on the builder's dashboard grid sends the
        `dashboard` the card sits on. A read-only collaborator's filter state is
        routed by that dashboard's stored links, as `view.get_chart_data`
        routes a reader's."""
        query, chart = self.make_content()
        self.share_workbook(chart, write=0)
        with as_user(OWNER):
            dashboard = frappe.get_doc(
                {
                    "doctype": DT.DASHBOARD,
                    "title": "Authoring API Test Dashboard",
                    "workbook": chart.workbook,
                    "items": self.grid_items(chart.name, query.name),
                }
            ).insert()

        answer = self.preview(
            OUTSIDER,
            chart_type="Table",
            query=query.name,
            config=table_config(),
            chart_name=chart.name,
            dashboard=dashboard.name,
            filters={"Description": {"operator": "contains", "value": "owner 1"}},
            force=True,
        )

        self.assertEqual(self.descriptions(answer), [OWNER_TODOS[0]])

    # @feature dashboard.filter-links permissions.chart-run-as-owner permissions.request-body-not-trusted
    def test_a_dashboard_routes_no_chart_it_does_not_carry(self):
        """`chart_preview.ts` sends the `dashboard` a builder card sits on, and a
        caller names any dashboard they can read. One of their own, with a
        filter linked to someone else's chart and no cell for it, must not cut
        that chart's rows by a column it never draws - through the builder or
        the view."""
        query, chart = self.make_content()
        self.share_workbook(chart, write=0)
        with as_user(OUTSIDER):
            workbook = frappe.get_doc(
                {"doctype": DT.WORKBOOK, "title": f"{WORKBOOK_TITLE} Outsider"}
            ).insert()
            dashboard = frappe.get_doc(
                {
                    "doctype": DT.DASHBOARD,
                    "title": "Authoring API Test Foreign Dashboard",
                    "workbook": workbook.name,
                    "items": self.grid_items(chart.name, query.name)[1:],
                }
            ).insert()

        filters = {"Description": {"operator": "contains", "value": "owner 1"}}
        with self.assertRaises(frappe.DoesNotExistError):
            self.preview(
                OUTSIDER,
                chart_type="Table",
                query=query.name,
                config=table_config(),
                chart_name=chart.name,
                dashboard=dashboard.name,
                filters=filters,
                force=True,
            )
        with as_user(OUTSIDER), db_connections(), self.assertRaises(frappe.DoesNotExistError):
            get_view_data(chart.name, dashboard=dashboard.name, filters=filters, force=True)

    # @feature dashboard.card-filter permissions.chart-run-as-owner
    def test_a_builder_card_says_whether_its_author_may_filter_it(self):
        """`chart_preview.ts` sends `chart_name` from the builder's dashboard
        grid, and `useChartCell` reads the answer to offer a table card's
        filter. Write on a chart run as its owner is trust to act as the owner,
        so an editor may filter it; a collaborator who may only read it may not."""
        query, chart = self.make_content()
        self.assertTrue(chart.run_as_owner)

        for write, may_filter in ((1, True), (0, False)):
            self.share_workbook(chart, write=write)
            card = self.preview(
                OUTSIDER,
                chart_type="Table",
                query=query.name,
                config=table_config(),
                chart_name=chart.name,
            )
            self.assertIs(card["can_filter"], may_filter, write)

    # @feature permissions.request-body-not-trusted charts.drill-breakdown permissions.chart-run-as-owner
    def test_a_reader_who_cannot_edit_the_chart_breaks_down_none_of_the_owners_rows(self):
        """`drill_api.ts` `fetchAuthoringDrillData` sends `chart_name` from a
        builder a read-only collaborator opened. The chart runs as its owner and
        they may not write it, so they get its picture and nothing behind it -
        whatever shape they send, their own operations included."""
        query, chart = self.make_filtered_content()
        self.share_workbook(chart, write=0)

        for shape in (
            {"operations": summarized_operations()},
            {"chart_type": "Table", "config": table_config()},
        ):
            result = self.drill(
                OUTSIDER,
                query=query.name,
                chart_name=chart.name,
                drill_stack=[breakdown_level("description")],
                **shape,
            )
            self.assertEqual(result["rows"], [])
            self.assertIn("not_permitted", result)

    # @feature permissions.request-body-not-trusted permissions.chart-run-as-owner
    def test_a_collaborator_who_may_edit_the_chart_previews_their_config_under_it(self):
        """`chart_preview.ts` from `ChartBuilder.vue`: a collaborator with write on
        the chart previews the config they are editing. Saving it would make it
        the chart's content, so it runs the way the chart declares."""
        query, chart = self.make_filtered_content()
        self.share_workbook(chart, write=1)

        with as_user(OUTSIDER):
            self.assertTrue(frappe.has_permission(DT.CHART, ptype="write", doc=chart.name))

        edited = self.preview(
            OUTSIDER,
            chart_type="Table",
            query=query.name,
            config=table_config(),
            chart_name=chart.name,
            force=True,
        )

        self.assertEqual(self.descriptions(edited), sorted(OWNER_TODOS))

    # @feature standard.read-only permissions.request-body-not-trusted
    def test_a_shipped_chart_gives_nobody_the_authors_answer(self):
        """`chart_preview.ts` names the chart the builder opened, and the builder
        draws a shipped chart's form read-only from its `as_dict`. Outside
        developer mode the owner, who holds write, gets the view's answer beside
        that form, as `view.get_chart` says they cannot write it."""
        query, chart = self.make_content()
        frappe.db.set_value(DT.WORKBOOK, chart.workbook, "is_standard", 1)

        def answer():
            return self.preview(
                OWNER, chart_type="Table", query=query.name, config=table_config(), chart_name=chart.name
            )

        with patch.dict(frappe.conf, {"developer_mode": 0}), as_user(OWNER):
            self.assertTrue(frappe.get_doc(DT.CHART, chart.name).as_dict().read_only)
            self.assertFalse(get_chart(chart.name)["can_write"])
            for key in ("sql", "operations"):
                self.assertNotIn(key, answer())

        with patch.dict(frappe.conf, {"developer_mode": 1}), as_user(OWNER):
            self.assertFalse(frappe.get_doc(DT.CHART, chart.name).as_dict().read_only)
            self.assertTrue(get_chart(chart.name)["can_write"])
            self.assertIn("sql", answer())

    # @feature charts.drill-rows charts.drill-rows-export permissions.chart-run-as-owner
    def test_a_builder_rows_level_reads_as_the_chart_does(self):
        """`chart_preview.ts` reads the builder's rows level through
        `get_drill_data`, `download_drill_rows` and `get_drill_rows_values`.
        Write on a chart run as its owner is trust to act as them, so a
        collaborator who may edit it reads the owner's rows there, as the card
        does. A chart run as its reader gives them their own."""
        query, chart = self.make_content()
        self.share_workbook(chart, write=1)
        frappe.db.set_single_value(DT.SETTINGS, "allow_download", 1)
        shape = {
            "query": query.name,
            "chart_type": "Table",
            "config": table_config(),
            "chart_name": chart.name,
        }
        level = [rows_level()]

        for run_as_owner, todos in ((1, sorted(OWNER_TODOS)), (0, [])):
            chart.db_set("run_as_owner", run_as_owner, update_modified=False)
            with as_user(OUTSIDER), db_connections():
                rows = get_authoring_drill(drill_stack=level, **shape)
                csv = download_authoring_drill_rows(drill_stack=level, **shape)
                values = get_authoring_drill_rows_values(drill_stack=level, column="description", **shape)

            self.assertEqual(self.descriptions(rows), todos, run_as_owner)
            self.assertEqual(sorted(value for value in values if value), todos, run_as_owner)
            for todo in OWNER_TODOS:
                self.assertEqual(todo in csv, bool(todos), run_as_owner)

    # @feature permissions.request-body-not-trusted
    def test_a_query_named_after_a_chart_gets_none_of_the_charts_references(self):
        """`resource.ts` and `query.ts` send `docs.name` from the client to
        `insights.api.run_doc_method`. A name no query holds passes as an unsaved
        query, so a chart's docname there must not authorise the chart's query."""
        query, chart = self.make_content()
        chart.db_set("visibility", "Private", update_modified=False)

        with as_user(OUTSIDER):
            self.assertFalse(frappe.has_permission(DT.QUERY, ptype="read", doc=query.name))

        docs = {
            "doctype": DT.QUERY,
            "name": chart.name,
            "use_live_connection": 1,
            "operations": [{"type": "source", "table": {"type": "query", "query_name": query.name}}],
        }
        with as_user(OUTSIDER), db_connections(), as_http_request():
            with self.assertRaises(frappe.PermissionError):
                run_doc_method("execute", frappe.as_json(docs), {"force": True})

    # @feature charts.measure-unit
    def test_both_feeds_carry_the_symbol_of_a_code_the_rows_hold(self):
        """A measure priced in a column's currency prints from the symbol map the
        session holds, and the response the rows came in is the only thing that
        fills it — the site is seeded with its own code and nothing else."""
        query, chart = self.make_content()
        config = table_config()
        config["values"] = [{**counted(), "format": "currency", "currency_column": "priority"}]
        with as_user(OWNER):
            chart.config = config
            chart.save()

        with as_user(OWNER), db_connections():
            authored = get_authoring_data(
                chart_type="Table", query=query.name, config=config, chart_name=chart.name, force=True
            )
        with as_user(READER), db_connections():
            read = get_view_data(chart=chart.name, force=True)

        # the todos carry the default priority, which is no ISO code, so the
        # symbol is the code itself
        for response in (authored, read):
            self.assertEqual(response["currency_symbols"]["Medium"]["symbol"], "Medium")

    # the view contract is unchanged

    # @feature permissions.view-sends-no-query
    def test_no_view_response_carries_the_derived_operations(self):
        query, chart = self.make_content()

        with as_user(READER), db_connections():
            responses = [
                get_chart(chart=chart.name),
                get_view_data(chart=chart.name, force=True),
            ]

        for response in responses:
            serialized = json.dumps(response, default=str)
            for leak in ("operations", "summarize", "tabToDo", query.name):
                self.assertNotIn(leak, serialized, f"{leak} must not reach a view")
            self.assertNotIn("sql", response)
