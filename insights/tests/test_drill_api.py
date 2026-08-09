import json
from unittest.mock import patch

import frappe

from insights.api.viewer import get_chart_data, get_drill_data
from insights.insights.doctype.insights_data_source_v3.insights_data_source_v3 import db_connections
from insights.resolver import ContentNotAvailableError
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import DT, as_user, create_user, delete_users, delete_workbooks

AUTHOR = "drill_api_author@test.com"
# in the audience, holds no Insights role at all - the desk viewer this ticket is for
DESK_USER = "drill_api_desk_user@test.com"
# holds an Insights role but is in no audience of the author's content
OUTSIDER = "drill_api_outsider@test.com"
GUEST = "Guest"

WORKBOOK_TITLE = "Drill API Test Workbook"
DASHBOARD_TITLE = "Drill API Test Dashboard"

TODO_PREFIX = "Drill API Test"
# the segments these tests click: two open todos of different priority, and one
# closed, so a filter that fails to narrow is visible in the rows
OPEN_HIGH = f"{TODO_PREFIX} open high"
OPEN_LOW = f"{TODO_PREFIX} open low"
CLOSED_HIGH = f"{TODO_PREFIX} closed high"
AUTHOR_TODOS = {
    OPEN_HIGH: ("Open", "High"),
    OPEN_LOW: ("Open", "Low"),
    CLOSED_HIGH: ("Closed", "High"),
}
OUTSIDER_TODO = f"{TODO_PREFIX} outsider open high"


def todo_operations():
    """A query over `tabToDo`, narrowed to this module's fixtures."""
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


def dimension(column_name, data_type="String", **extra):
    return {
        "column_name": column_name,
        "dimension_name": column_name,
        "data_type": data_type,
        **extra,
    }


def count(measure_name="Todos"):
    return {
        "measure_name": measure_name,
        "column_name": "name",
        "aggregation": "count",
        "data_type": "Integer",
    }


def bar_config():
    """Todos by status, counted — the chart every mechanics test clicks on."""
    return {
        "limit": 50,
        "x_axis": {"dimension": dimension("status")},
        "y_axis": {"series": []},
        "order_by": [],
    }


def pivot_config(values=None):
    """The same counts, spread across priority: a cell pins a row and a column."""
    return {
        "limit": 50,
        "rows": [dimension("status")],
        "columns": [dimension("priority")],
        "values": values or [count()],
        "order_by": [],
    }


def records_level(filters=None, measure=None):
    return {"segment_filters": filters or [], "action": {"records": True, "measure": measure}}


def breakdown_level(dimension_name, filters=None, measure=None):
    return {
        "segment_filters": filters or [],
        "action": {"breakdown": dimension_name, "measure": measure},
    }


def equals(column, value):
    return {"column": column, "operator": "=", "value": value}


class TestDrillAPI(InsightsIntegrationTestCase):
    SAVEPOINT = "test_drill_api"

    @classmethod
    def before_class(cls):
        cls.original_enable_permissions = frappe.db.get_single_value(DT.SETTINGS, "enable_permissions")
        frappe.db.set_single_value(DT.SETTINGS, "enable_permissions", 0)
        cls.cleanup()

        create_user(AUTHOR, first_name="Drill", last_name="Author", roles="Insights User")
        create_user(OUTSIDER, first_name="Drill", last_name="Outsider", roles="Insights User")
        create_user(DESK_USER, first_name="Drill", last_name="Desk User")

        for description, (status, priority) in AUTHOR_TODOS.items():
            cls.make_todo(description, status, priority, AUTHOR)
        cls.make_todo(OUTSIDER_TODO, "Open", "High", OUTSIDER)

    @classmethod
    def make_todo(cls, description, status, priority, allocated_to):
        frappe.get_doc(
            {
                "doctype": "ToDo",
                "description": description,
                "status": status,
                "priority": priority,
                "allocated_to": allocated_to,
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
        delete_users(AUTHOR, OUTSIDER, DESK_USER)

    # fixtures

    def make_content(
        self,
        chart_type="Bar",
        config=None,
        visibility="Everyone",
        title=DASHBOARD_TITLE,
        operations=None,
        authority="Author",
    ):
        """A dashboard the author owns, with one chart and one filter linked to it."""
        with as_user(AUTHOR):
            workbook = frappe.get_doc({"doctype": DT.WORKBOOK, "title": WORKBOOK_TITLE}).insert()
            query = frappe.get_doc(
                {
                    "doctype": DT.QUERY,
                    "title": "Drill API Test Query",
                    "workbook": workbook.name,
                    "use_live_connection": 1,
                    "is_builder_query": 1,
                    "operations": operations or todo_operations(),
                }
            ).insert()
            chart = frappe.get_doc(
                {
                    "doctype": DT.CHART,
                    "title": "Drill API Test Chart",
                    "workbook": workbook.name,
                    "query": query.name,
                    "chart_type": chart_type,
                    "config": config if config is not None else bar_config(),
                    "visibility": "Private",
                }
            ).insert()
            dashboard = frappe.get_doc(
                {
                    "doctype": DT.DASHBOARD,
                    "title": title,
                    "workbook": workbook.name,
                    "visibility": visibility,
                    "items": [
                        {
                            "type": "chart",
                            "chart": chart.name,
                            "layout": {"i": "chart-1", "x": 0, "y": 1, "w": 10, "h": 8},
                        },
                        {
                            "type": "filter",
                            "filter_name": "Description",
                            "filter_type": "String",
                            "links": {chart.name: f"`{query.name}`.`description`"},
                            "layout": {"i": "filter-1", "x": 0, "y": 0, "w": 4, "h": 1},
                        },
                    ],
                }
            ).insert()

        chart = frappe.get_doc(DT.CHART, chart.name)
        chart.db_set("data_authority", authority, update_modified=False)

        return (
            frappe.get_doc(DT.QUERY, query.name),
            frappe.get_doc(DT.CHART, chart.name),
            frappe.get_doc(DT.DASHBOARD, dashboard.name),
        )

    def drill(self, user, chart, dashboard=None, **kwargs):
        with as_user(user), db_connections():
            return get_drill_data(chart=chart, dashboard=dashboard, **kwargs)

    def descriptions(self, result):
        return sorted(row["description"] for row in result["rows"])

    def column_names(self, result):
        return [column["name"] for column in result["columns"]]

    # the two things a level can ask for

    def test_a_records_level_returns_the_rows_behind_the_segment(self):
        _, chart, dashboard = self.make_content()

        result = self.drill(
            DESK_USER,
            chart.name,
            dashboard.name,
            drill_stack=[records_level(filters=[equals("status", "Open")], measure="count_of_rows")],
        )

        self.assertEqual(self.descriptions(result), sorted([OPEN_HIGH, OPEN_LOW]))
        # every column the author's query selects, which is the whole exposure
        # bound: no column picking on top of it
        for column in ("description", "status", "priority", "name"):
            self.assertIn(column, self.column_names(result))
        # what the page is a page of, so the dialog can state its bound
        self.assertEqual(result["total_row_count"], 2)

    def test_a_breakdown_level_groups_the_segment_by_the_chosen_dimension(self):
        _, chart, dashboard = self.make_content()

        result = self.drill(
            DESK_USER,
            chart.name,
            dashboard.name,
            drill_stack=[
                breakdown_level("priority", filters=[equals("status", "Open")], measure="count_of_rows")
            ],
        )

        self.assertEqual(self.column_names(result), ["priority", "count_of_rows"])
        self.assertEqual(
            sorted((row["priority"], row["count_of_rows"]) for row in result["rows"]),
            [("High", 1), ("Low", 1)],
        )

    def test_a_breakdown_by_a_datetime_buckets_it_instead_of_grouping_moments(self):
        """Grouped raw, a timestamp puts every row in its own second."""
        _, chart, dashboard = self.make_content()

        result = self.drill(
            DESK_USER,
            chart.name,
            dashboard.name,
            drill_stack=[breakdown_level("creation", measure="count_of_rows")],
        )

        # the fixtures are made in one breath, so a month bucket holds them all
        self.assertEqual(len(result["rows"]), 1)
        self.assertEqual(result["rows"][0]["count_of_rows"], len(AUTHOR_TODOS))

    def test_a_breakdown_is_cut_to_a_ranking(self):
        """The level answers which slice explains the number, so it ranks a few.

        The cut is proven against a smaller bound than the shipped one: the
        fixtures hold three descriptions, and committing twenty-odd more would
        put them in front of every other test in this class.
        """
        _, chart, dashboard = self.make_content()

        with patch("insights.insights.doctype.insights_chart_v3.chart_drill.BREAKDOWN_SIZE", 2):
            result = self.drill(
                DESK_USER,
                chart.name,
                dashboard.name,
                drill_stack=[breakdown_level("description", measure="count_of_rows")],
            )

        self.assertEqual(len(result["rows"]), 2)
        # the dialog says "top 2 of 3", so the count has to see past the cut
        self.assertEqual(result["total_row_count"], 3)

    def test_a_records_level_is_not_cut_to_a_ranking(self):
        """A records page is bounded by the page size, not the ranking size."""
        _, chart, dashboard = self.make_content()

        with patch("insights.insights.doctype.insights_chart_v3.chart_drill.BREAKDOWN_SIZE", 1):
            result = self.drill(
                DESK_USER,
                chart.name,
                dashboard.name,
                drill_stack=[records_level(measure="count_of_rows")],
            )

        self.assertEqual(len(result["rows"]), 3)

    def test_a_breakdown_carries_the_measure_the_click_landed_on(self):
        _, chart, dashboard = self.make_content(
            chart_type="Table",
            config={
                "limit": 50,
                "rows": [dimension("status")],
                "columns": [],
                "values": [count("Todos"), count("Assignments")],
                "order_by": [],
            },
        )

        result = self.drill(
            DESK_USER,
            chart.name,
            dashboard.name,
            drill_stack=[breakdown_level("priority", filters=[equals("status", "Open")], measure="Todos")],
        )

        self.assertEqual(self.column_names(result), ["priority", "Todos"])

    def test_segments_accumulate_down_the_stack(self):
        _, chart, dashboard = self.make_content()

        result = self.drill(
            DESK_USER,
            chart.name,
            dashboard.name,
            drill_stack=[
                breakdown_level("priority", filters=[equals("status", "Open")], measure="count_of_rows"),
                records_level(filters=[equals("priority", "High")], measure="count_of_rows"),
            ],
        )

        # the status of the first level and the priority of the second, both
        self.assertEqual(self.descriptions(result), [OPEN_HIGH])

    def test_a_number_card_drills_on_an_empty_segment(self):
        _, chart, dashboard = self.make_content(
            chart_type="Number", config={"number_columns": [count("Todos")]}
        )

        result = self.drill(
            DESK_USER, chart.name, dashboard.name, drill_stack=[records_level(measure="Todos")]
        )

        self.assertEqual(self.descriptions(result), sorted(AUTHOR_TODOS))

    def test_a_conditional_measure_carries_its_condition_into_the_rows(self):
        _, chart, dashboard = self.make_content(
            chart_type="Number",
            config={
                "number_columns": [
                    {
                        "measure_name": "Open",
                        "data_type": "Integer",
                        "expression": {"type": "expression", "expression": "count_if(status == 'Open')"},
                    }
                ]
            },
        )

        result = self.drill(
            DESK_USER, chart.name, dashboard.name, drill_stack=[records_level(measure="Open")]
        )

        # the rows behind the number are the ones the measure counted
        self.assertEqual(self.descriptions(result), sorted([OPEN_HIGH, OPEN_LOW]))

    # a segment the chart spread across its columns

    def test_a_pivot_cell_pins_the_row_and_the_column(self):
        _, chart, dashboard = self.make_content(chart_type="Table", config=pivot_config())

        result = self.drill(
            DESK_USER,
            chart.name,
            dashboard.name,
            # the cell under the "High" column, on the "Open" row: the row
            # dimension and the column dimension pin together
            drill_stack=[
                records_level(filters=[equals("status", "Open"), equals("priority", "High")], measure="Todos")
            ],
        )

        self.assertEqual(self.descriptions(result), [OPEN_HIGH])

    def test_a_split_by_segment_pins_the_axis_value_and_the_series(self):
        _, chart, dashboard = self.make_content(
            chart_type="Bar",
            config={
                "limit": 50,
                "x_axis": {"dimension": dimension("status")},
                "split_by": {"dimension": dimension("priority")},
                "y_axis": {"series": [{"measure": count("Todos")}, {"measure": count("Assignments")}]},
                "order_by": [],
            },
        )

        result = self.drill(
            DESK_USER,
            chart.name,
            dashboard.name,
            # the axis value and the series value, both pinned by the one click
            drill_stack=[
                breakdown_level(
                    "description",
                    filters=[equals("status", "Open"), equals("priority", "High")],
                    measure="Todos",
                )
            ],
        )

        self.assertEqual(self.column_names(result), ["description", "Todos"])
        self.assertEqual([row["description"] for row in result["rows"]], [OPEN_HIGH])

    def test_a_date_segment_covers_the_bucket_the_chart_grouped_by(self):
        _, chart, dashboard = self.make_content(
            chart_type="Line",
            config={
                "limit": 50,
                "x_axis": {"dimension": dimension("creation", "Datetime", granularity="month")},
                "y_axis": {"series": []},
                "order_by": [],
            },
        )
        this_month = frappe.utils.get_first_day(frappe.utils.today())

        rows = self.drill(
            DESK_USER,
            chart.name,
            dashboard.name,
            drill_stack=[records_level(filters=[equals("creation", str(this_month))])],
        )
        empty = self.drill(
            DESK_USER,
            chart.name,
            dashboard.name,
            drill_stack=[
                records_level(filters=[equals("creation", str(frappe.utils.add_months(this_month, -1)))])
            ],
        )

        self.assertEqual(self.descriptions(rows), sorted(AUTHOR_TODOS))
        self.assertEqual(empty["rows"], [])

    # the wire cannot widen what the chart exposes

    def test_a_column_that_is_not_on_the_surface_is_refused(self):
        _, chart, dashboard = self.make_content()

        for stack in (
            [records_level(filters=[equals("tabUser.password", "x")])],
            [breakdown_level("password")],
        ):
            with self.assertRaises(frappe.ValidationError) as raised:
                self.drill(DESK_USER, chart.name, dashboard.name, drill_stack=stack)
            self.assertIn("is not a column", str(raised.exception))

    def test_no_drill_response_carries_the_query_behind_the_chart(self):
        query, chart, dashboard = self.make_content()

        result = self.drill(
            DESK_USER,
            chart.name,
            dashboard.name,
            drill_stack=[records_level(filters=[equals("status", "Open")])],
        )

        serialized = json.dumps(result, default=str)
        for leak in ("operations", "raw_sql", "tabToDo", query.name):
            self.assertNotIn(leak, serialized, f"{leak} must not reach a viewer")
        self.assertNotIn("sql", result)

    # what the menu offers before anything is clicked

    def test_the_chart_response_offers_the_dimensions_of_the_pre_summarize_surface(self):
        _, chart, dashboard = self.make_content()

        with as_user(DESK_USER), db_connections():
            response = get_chart_data(chart=chart.name, dashboard=dashboard.name, force=True)

        dimensions = {d["name"]: d["type"] for d in response["drill"]["dimensions"]}
        # the surface underneath the summarize, so a column the chart does not
        # draw is still a candidate
        self.assertEqual(dimensions.get("priority"), "String")
        self.assertEqual(dimensions.get("status"), "String")
        self.assertEqual(dimensions.get("creation"), "Datetime")
        # what the summarize produced is not on the surface it summarized
        self.assertNotIn("count_of_rows", dimensions)
        # and neither is anything that measures rather than groups
        self.assertNotIn("docstatus", dimensions)

    # the record behind a row

    def test_a_records_row_names_the_desk_record_it_opens(self):
        _, chart, dashboard = self.make_content()

        result = self.drill(
            DESK_USER,
            chart.name,
            dashboard.name,
            drill_stack=[records_level(filters=[equals("status", "Open")])],
        )

        self.assertEqual(result["record_link"], {"doctype": "ToDo", "column": "name"})

    def test_a_renamed_name_column_carries_no_record_link(self):
        renamed = [
            *todo_operations(),
            {
                "type": "rename",
                "column": {"type": "column", "column_name": "name"},
                "new_name": "todo_id",
            },
        ]
        _, chart, dashboard = self.make_content(operations=renamed)

        result = self.drill(
            DESK_USER,
            chart.name,
            dashboard.name,
            drill_stack=[records_level(filters=[equals("status", "Open")])],
        )

        # the convention missed, so the client is told nothing rather than told
        # a record that might be the wrong one
        self.assertNotIn("record_link", result)

    def test_only_a_records_level_carries_a_record_link(self):
        _, chart, dashboard = self.make_content()

        result = self.drill(
            DESK_USER,
            chart.name,
            dashboard.name,
            drill_stack=[breakdown_level("priority", filters=[equals("status", "Open")])],
        )

        self.assertNotIn("record_link", result)

    # dashboard filters

    def test_dashboard_filter_state_reaches_the_drill(self):
        _, chart, dashboard = self.make_content()

        result = self.drill(
            DESK_USER,
            chart.name,
            dashboard.name,
            filters={"Description": {"operator": "contains", "value": "open low"}},
            drill_stack=[records_level(filters=[equals("status", "Open")])],
        )

        # the rows agree with the number the filtered card was showing
        self.assertEqual(self.descriptions(result), [OPEN_LOW])

    # who may drill

    def test_an_audience_member_without_an_insights_role_drills_what_they_can_see(self):
        _, chart, dashboard = self.make_content()
        self.assertNotIn("Insights User", frappe.get_roles(DESK_USER))

        result = self.drill(
            DESK_USER, chart.name, dashboard.name, drill_stack=[records_level(measure="count_of_rows")]
        )

        self.assertEqual(self.descriptions(result), sorted(AUTHOR_TODOS))

    def test_the_drill_runs_under_the_authority_the_chart_declares(self):
        _, chart, dashboard = self.make_content(authority="Viewer")

        result = self.drill(
            DESK_USER, chart.name, dashboard.name, drill_stack=[records_level(measure="count_of_rows")]
        )

        # `Viewer` is the engine's native permission application, so a roleless
        # viewer sees none of the author's rows behind the number either
        self.assertEqual(self.descriptions(result), [])

    def test_an_outsider_is_answered_like_a_missing_reference(self):
        _, chart, dashboard = self.make_content(visibility="Private")

        with as_user(OUTSIDER):
            for reference, on_dashboard in ((chart.name, None), (chart.name, dashboard.name)):
                with self.assertRaises(ContentNotAvailableError):
                    get_drill_data(chart=reference, dashboard=on_dashboard, drill_stack=[records_level()])

    def test_a_guest_gets_no_drill_on_public_content(self):
        _, chart, dashboard = self.make_content()
        dashboard.db_set("visibility", "Public", update_modified=False)

        with as_user(GUEST), db_connections():
            # the picture is public, and stays a picture
            response = get_chart_data(chart=chart.name, dashboard=dashboard.name, force=True)
            self.assertEqual(response["drill"]["dimensions"], [])

            with self.assertRaises(frappe.PermissionError) as raised:
                get_drill_data(chart=chart.name, dashboard=dashboard.name, drill_stack=[records_level()])

        self.assertNotIsInstance(raised.exception, ContentNotAvailableError)

    def test_a_stack_without_a_level_asks_for_nothing(self):
        _, chart, dashboard = self.make_content()

        with self.assertRaises(frappe.ValidationError):
            self.drill(DESK_USER, chart.name, dashboard.name, drill_stack=[])
