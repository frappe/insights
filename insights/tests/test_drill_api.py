"""What a number a chart drew is made of, level by level.

The walk is `chart_drill`'s: a chart document, a stack of levels, and the rows
behind the segment the stack describes. It is tested at the layer, under the
owner who built the chart, because the layer is what every endpoint shares.
`test_authoring_api` covers the builder's endpoint and what it adds.
"""

import json
import re
from unittest.mock import patch

import frappe
import frappe.share

from insights.api.authoring import get_chart_data as get_authoring_chart_data
from insights.api.authoring import get_drill_data as get_authoring_drill_data
from insights.api.authoring import get_drill_rows_range as get_authoring_drill_rows_range
from insights.api.authoring import get_drill_rows_values as get_authoring_drill_rows_values
from insights.api.view import (
    download_drill_rows,
    get_chart_data,
    get_drill_data,
    get_drill_rows_range,
    get_drill_rows_values,
)
from insights.insights.doctype.insights_chart_v3.chart_drill import drill_data, drill_dimensions
from insights.insights.doctype.insights_chart_v3.insights_chart_v3 import InsightsChartv3
from insights.insights.doctype.insights_dashboard_v3.insights_dashboard_v3 import route_filters
from insights.insights.doctype.insights_data_source_v3.insights_data_source_v3 import db_connections
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import DT, as_user, create_user, delete_users, delete_workbooks

OWNER = "drill_api_owner@test.com"
# visibility admits them, but they hold no Insights role: a desk user
DESK_USER = "drill_api_desk_user@test.com"
# holds an Insights role, but the owner's content never admits them
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
OWNER_TODOS = {
    OPEN_HIGH: ("Open", "High"),
    OPEN_LOW: ("Open", "Low"),
    CLOSED_HIGH: ("Closed", "High"),
}
OUTSIDER_TODO = f"{TODO_PREFIX} outsider open high"
# those three by the number a ranked rows page puts first, biggest first
BY_WEIGHT = sorted(OWNER_TODOS, key=len, reverse=True)

# the todos the ordered tests break down: dated, spread unevenly over one year,
# so chronological order and a ranking by the measure disagree about every
# position. The prefix shares no words with `TODO_PREFIX`, so the two sets never
# land in the same query
TIMELINE_PREFIX = "Drill API Dated"
TIMELINE_TODOS = {
    f"{TIMELINE_PREFIX} january": ("2024-01-15", "Low"),
    f"{TIMELINE_PREFIX} february one": ("2024-02-15", "Low"),
    f"{TIMELINE_PREFIX} february two": ("2024-02-16", "Low"),
    f"{TIMELINE_PREFIX} february three": ("2024-02-17", "High"),
    f"{TIMELINE_PREFIX} june": ("2024-06-15", "Low"),
    f"{TIMELINE_PREFIX} december": ("2024-12-15", "High"),
}
# what those dates hold, month by month, oldest first
TIMELINE_MONTHS = ["2024-01-01", "2024-02-01", "2024-06-01", "2024-12-01"]
TIMELINE_COUNTS = [1, 3, 1, 1]
# the bucket the nested tests click into, and the one priority inside it that
# does not fill it — so a level that fails to narrow is visible in the rows
FEBRUARY = sorted(d for d, (date, _) in TIMELINE_TODOS.items() if date.startswith("2024-02"))
FEBRUARY_LOW = sorted(
    d for d, (date, priority) in TIMELINE_TODOS.items() if date.startswith("2024-02") and priority == "Low"
)


def todo_operations(prefix=TODO_PREFIX):
    """A query over `tabToDo`, narrowed to one of this module's fixture sets."""
    return [
        {
            "type": "source",
            "table": {"type": "table", "data_source": "Site DB", "table_name": "tabToDo"},
        },
        {
            "type": "filter",
            "column": {"type": "column", "column_name": "description"},
            "operator": "contains",
            "value": prefix,
        },
    ]


def weighted_operations():
    """The same query with a number per row, which is what a rows page ranks by.

    `tabToDo` carries no measurable column of its own, so the tests that turn on
    the ranking derive one the fixtures already differ on.
    """
    return [
        *todo_operations(),
        {
            "type": "mutate",
            "new_name": "weight",
            "data_type": "Integer",
            "expression": {"type": "expression", "expression": "description.length()"},
        },
    ]


def bucketed_operations():
    """The same query with a column that holds `Others` in every row.

    A split keeps its top values and relabels the rest `Others`. This column
    checks that a drill reads a real `Others` value as itself.
    """
    return [
        *todo_operations(),
        {
            "type": "mutate",
            "new_name": "bucket",
            "data_type": "String",
            "expression": {"type": "expression", "expression": "ibis.literal('Others')"},
        },
    ]


def half_others_operations():
    """The same query with a column that really holds `Others` for some rows.

    It holds two values, one of them `Others`. A split capped at one value
    shows a single `Others` series that holds both.
    """
    return [
        *todo_operations(),
        {
            "type": "mutate",
            "new_name": "bucket",
            "data_type": "String",
            "expression": {
                "type": "expression",
                "expression": "ibis.cases((priority == 'High', ibis.literal('Others')), else_=priority)",
            },
        },
    ]


def has_role_operations():
    """A query over a child table — a `tabHas Role` row belongs to a User."""
    return [
        {
            "type": "source",
            "table": {"type": "table", "data_source": "Site DB", "table_name": "tabHas Role"},
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


def weight(measure_name="Weight"):
    """A measure over a number, which is the only kind a rows page can rank by."""
    return {
        "measure_name": measure_name,
        "column_name": "weight",
        "aggregation": "sum",
        "data_type": "Integer",
    }


def average(measure_name="Average Order"):
    """A measure whose group values do not add up to the value of the whole."""
    return {
        "measure_name": measure_name,
        "column_name": "idx",
        "aggregation": "avg",
        "data_type": "Decimal",
    }


def bar_config_over(column_name):
    """The same bar chart, grouped by a column of the table under test."""
    return {
        "limit": 50,
        "x_axis": {"dimension": dimension(column_name)},
        "y_axis": {"series": []},
        "order_by": [],
    }


def bar_config(measures=None):
    """Todos by status, counted — the chart every mechanics test clicks on.

    A chart that declares no series of its own counts rows, which is what the
    mechanics tests click. `measures` names them instead, for the tests that
    turn on which measure a level carries.
    """
    return {
        "limit": 50,
        "x_axis": {"dimension": dimension("status")},
        "y_axis": {"series": [{"measure": measure} for measure in measures or []]},
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


def number_config():
    """A card reading one number, measured against a target.

    The target is a measure of the card's own result and is summarized beside
    the reading, so a card carries more measures than it draws.
    """
    return {
        "limit": 50,
        "number_columns": [count("Todos")],
        "number_column_options": [{"target": {"measure": average()}}],
        "order_by": [],
    }


def rows_level(filters=None, measure=None, drawn_on=None):
    level = {"segment_filters": filters or [], "action": {"rows": True, "measure": measure}}
    if drawn_on:
        level["drawn_on"] = drawn_on

    return level


def breakdown_level(dimension_name, filters=None, measure=None, granularity=None):
    action = {"breakdown": dimension_name, "measure": measure}
    if granularity:
        action["granularity"] = granularity

    return {"segment_filters": filters or [], "action": action}


def rule(column, operator, value):
    """One (column, operator, value) triple. Segments and reader filters both use it."""
    return {"column": column, "operator": operator, "value": value}


def equals(column, value):
    return rule(column, "=", value)


def filter_group(column_name, operator, value):
    """One routed filter group, shaped the way `route_filters` writes it."""
    return {
        "type": "filter_group",
        "logical_operator": "And",
        "filters": [
            {
                "type": "filter",
                "column": {"type": "column", "column_name": column_name},
                "operator": operator,
                "value": value,
            }
        ],
    }


class TestDrillAPI(InsightsIntegrationTestCase):
    SAVEPOINT = "test_drill_api"

    @classmethod
    def before_class(cls):
        cls.original_enable_permissions = frappe.db.get_single_value(DT.SETTINGS, "enable_permissions")
        frappe.db.set_single_value(DT.SETTINGS, "enable_permissions", 0)
        # allow file downloads. The export tests turn it off and on themselves
        cls.original_allow_download = frappe.db.get_single_value(DT.SETTINGS, "allow_download")
        frappe.db.set_single_value(DT.SETTINGS, "allow_download", 1)
        cls.cleanup()

        create_user(OWNER, first_name="Drill", last_name="Owner", roles="Insights User")
        create_user(OUTSIDER, first_name="Drill", last_name="Outsider", roles="Insights User")
        create_user(DESK_USER, first_name="Drill", last_name="Desk User")

        for description, (status, priority) in OWNER_TODOS.items():
            cls.make_todo(description, status, priority, OWNER)
        cls.make_todo(OUTSIDER_TODO, "Open", "High", OUTSIDER)
        for description, (date, priority) in TIMELINE_TODOS.items():
            cls.make_todo(description, "Open", priority, OWNER, date=date)

    @classmethod
    def make_todo(cls, description, status, priority, allocated_to, date=None):
        frappe.get_doc(
            {
                "doctype": "ToDo",
                "description": description,
                "status": status,
                "priority": priority,
                "date": date,
                "allocated_to": allocated_to,
                "assigned_by": "Administrator",
            }
        ).insert(ignore_permissions=True)

    @classmethod
    def after_class(cls):
        cls.cleanup()
        frappe.db.set_single_value(DT.SETTINGS, "enable_permissions", cls.original_enable_permissions)
        frappe.db.set_single_value(DT.SETTINGS, "allow_download", cls.original_allow_download)

    @classmethod
    def cleanup(cls):
        delete_workbooks(title_prefix=WORKBOOK_TITLE)
        for prefix in (TODO_PREFIX, TIMELINE_PREFIX):
            for todo in frappe.get_all(
                "ToDo", filters={"description": ["like", f"%{prefix}%"]}, pluck="name"
            ):
                frappe.delete_doc("ToDo", todo, force=True, ignore_permissions=True)
        delete_users(OWNER, OUTSIDER, DESK_USER)

    # fixtures

    def make_content(
        self,
        chart_type="Bar",
        config=None,
        visibility="Everyone",
        title=DASHBOARD_TITLE,
        operations=None,
        run_as_owner=1,
    ):
        """A dashboard the owner owns, with one chart and one filter linked to it."""
        with as_user(OWNER):
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
        chart.db_set("run_as_owner", run_as_owner, update_modified=False)

        return (
            frappe.get_doc(DT.QUERY, query.name),
            frappe.get_doc(DT.CHART, chart.name),
            frappe.get_doc(DT.DASHBOARD, dashboard.name),
        )

    def drill(self, user, chart, dashboard=None, filters=None, **kwargs):
        """One walk down `chart`, under `user`, with the dashboard's filter state routed."""
        adhoc_filters = None
        if dashboard and filters:
            items = frappe.db.get_value(DT.DASHBOARD, dashboard, "items")
            adhoc_filters = route_filters(items, chart, filters)

        with as_user(user), db_connections():
            return drill_data(frappe.get_doc(DT.CHART, chart), adhoc_filters=adhoc_filters, **kwargs)

    def column_names(self, result):
        return [column["name"] for column in result["columns"]]

    def buckets(self, result, column="date"):
        """The dimension values of a breakdown, in the order they came back."""
        return [str(row[column])[:10] for row in result["rows"]]

    def timeline(self, **kwargs):
        """A chart over the dated fixtures, which is what the ordered tests click."""
        return self.make_content(operations=todo_operations(TIMELINE_PREFIX), **kwargs)

    # the two things a level can ask for

    # @feature charts.drill-rows
    def test_a_rows_level_returns_the_rows_behind_the_segment(self):
        _, chart, dashboard = self.make_content()

        result = self.drill(
            OWNER,
            chart.name,
            dashboard.name,
            drill_stack=[rows_level(filters=[equals("status", "Open")], measure="count_of_rows")],
        )

        self.assertEqual(self.descriptions(result), sorted([OPEN_HIGH, OPEN_LOW]))
        # every column the author's query selects, which is the whole exposure
        # bound: no column picking on top of it
        for column in ("description", "status", "priority", "name"):
            self.assertIn(column, self.column_names(result))
        # what the page is a page of, so the dialog can state its bound
        self.assertEqual(result["total_row_count"], 2)

    # @feature charts.drill-breakdown
    def test_a_breakdown_level_groups_the_segment_by_the_chosen_dimension(self):
        _, chart, dashboard = self.make_content()

        result = self.drill(
            OWNER,
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

    # @feature charts.drill-grain
    def test_a_breakdown_by_a_datetime_buckets_it_instead_of_grouping_moments(self):
        """Grouped raw, a timestamp puts every row in its own second."""
        _, chart, dashboard = self.make_content()

        result = self.drill(
            OWNER,
            chart.name,
            dashboard.name,
            drill_stack=[breakdown_level("creation", measure="count_of_rows")],
        )

        # the fixtures are created within one second, so the span asks for the finest
        # grain `GRAINS` offers and they all land within a bucket of it
        self.assertEqual(result["granularity"], "minute")
        self.assertEqual(sum(row["count_of_rows"] for row in result["rows"]), len(OWNER_TODOS))

    # @feature charts.drill-breakdown
    def test_a_breakdown_is_cut_to_a_ranking(self):
        """The level answers which group explains the number, so it ranks a few.

        The cut is proven against a smaller bound than the shipped one: the
        fixtures hold three descriptions, and committing twenty-odd more would
        put them in front of every other test in this class.
        """
        _, chart, dashboard = self.make_content()

        with patch("insights.insights.doctype.insights_chart_v3.chart_drill.BREAKDOWN_SIZE", 2):
            result = self.drill(
                OWNER,
                chart.name,
                dashboard.name,
                drill_stack=[breakdown_level("description", measure="count_of_rows")],
            )

        self.assertEqual(len(result["rows"]), 2)
        # the dialog says "top 2 of 3", so the count has to see past the cut
        self.assertEqual(result["total_row_count"], 3)

    # @feature charts.drill-rows
    def test_a_rows_level_is_not_cut_to_a_ranking(self):
        """A rows page is bounded by the page size, not the ranking size."""
        _, chart, dashboard = self.make_content()

        with patch("insights.insights.doctype.insights_chart_v3.chart_drill.BREAKDOWN_SIZE", 1):
            result = self.drill(
                OWNER,
                chart.name,
                dashboard.name,
                drill_stack=[rows_level(measure="count_of_rows")],
            )

        self.assertEqual(len(result["rows"]), 3)

    # the order a rows page comes back in

    # @feature charts.drill-rows
    def test_a_rows_page_is_ranked_by_the_measure_that_was_clicked(self):
        """One page is shown, so it holds the rows that made the number biggest."""
        _, chart, dashboard = self.make_content(
            operations=weighted_operations(), config=bar_config([weight()])
        )

        result = self.drill(OWNER, chart.name, dashboard.name, drill_stack=[rows_level(measure="Weight")])

        self.assertEqual([row["description"] for row in result["rows"]], BY_WEIGHT)

    # @feature charts.drill-rows
    def test_a_rows_page_that_names_no_measure_follows_the_chart_s_own(self):
        _, chart, dashboard = self.make_content(
            operations=weighted_operations(), config=bar_config([weight()])
        )

        result = self.drill(OWNER, chart.name, dashboard.name, drill_stack=[rows_level()])

        self.assertEqual([row["description"] for row in result["rows"]], BY_WEIGHT)

    # @feature charts.drill-rows
    def test_a_measure_with_no_number_under_it_leaves_the_page_unranked(self):
        """Counting rows ranks none of them, and a name is no size."""
        _, chart, dashboard = self.make_content(config=bar_config([count()]))

        result = self.drill(OWNER, chart.name, dashboard.name, drill_stack=[rows_level(measure="Todos")])

        self.assertEqual(self.descriptions(result), sorted(OWNER_TODOS))

    # what a reader asks of a rows level
    #
    # A View never gets the pipeline. The reader asks for a sort, a find and a
    # page by name, and the server applies them inside the same cut.

    # @feature charts.drill-rows-reading
    def test_a_sort_the_reader_named_replaces_the_ranking_the_click_implied(self):
        _, chart, dashboard = self.make_content(
            operations=weighted_operations(), config=bar_config([weight()])
        )

        result = self.drill(
            OWNER,
            chart.name,
            dashboard.name,
            drill_stack=[rows_level(measure="Weight")],
            sort=[{"column": "description", "direction": "desc"}],
        )

        self.assertEqual([row["description"] for row in result["rows"]], sorted(OWNER_TODOS, reverse=True))
        self.assertNotEqual([row["description"] for row in result["rows"]], BY_WEIGHT)

    # @feature charts.drill-rows-reading
    def test_the_first_column_of_a_sort_is_the_one_the_rows_run_by(self):
        """The engine merges chained sorts and the last one it is given wins, so
        the column the reader listed first has to be written last."""
        _, chart, dashboard = self.make_content()

        result = self.drill(
            OWNER,
            chart.name,
            dashboard.name,
            drill_stack=[rows_level()],
            sort=[
                {"column": "status", "direction": "asc"},
                {"column": "description", "direction": "desc"},
            ],
        )

        self.assertEqual([row["description"] for row in result["rows"]], [CLOSED_HIGH, OPEN_LOW, OPEN_HIGH])

    # @feature charts.drill-rows-reading
    def test_a_find_narrows_the_rows_and_the_total_they_are_counted_against(self):
        _, chart, dashboard = self.make_content()

        result = self.drill(OWNER, chart.name, dashboard.name, drill_stack=[rows_level()], find="open")

        self.assertEqual(self.descriptions(result), sorted([OPEN_HIGH, OPEN_LOW]))
        # the total the dialog shows counts only the rows the find kept
        self.assertEqual(result["total_row_count"], 2)

    # @feature charts.drill-rows-reading
    def test_a_find_reads_the_text_of_the_surface_and_leaves_its_dates_alone(self):
        """A find is a text match. A date holds no substring a reader types, and
        matching one is an error rather than a miss."""
        _, chart, dashboard = self.make_content(
            operations=[
                *todo_operations(TIMELINE_PREFIX),
                {"type": "select", "column_names": ["description", "date"]},
            ],
            config=bar_config_over("description"),
        )

        found = self.drill(OWNER, chart.name, dashboard.name, drill_stack=[rows_level()], find="february")
        self.assertEqual(self.descriptions(found), FEBRUARY)

        dated = self.drill(OWNER, chart.name, dashboard.name, drill_stack=[rows_level()], find="2024")
        self.assertEqual(dated["rows"], [])
        self.assertEqual(dated["total_row_count"], 0)

    # @feature charts.drill-rows-reading
    def test_a_find_on_a_cut_with_nothing_to_match_keeps_no_rows(self):
        """The engine treats an empty find group as no filter. It returned every
        row, and the reader took the whole cut as matches for their term."""
        _, chart, dashboard = self.make_content(
            operations=[
                *todo_operations(TIMELINE_PREFIX),
                {"type": "select", "column_names": ["date"]},
            ],
            config=bar_config_over("date"),
        )

        result = self.drill(OWNER, chart.name, dashboard.name, drill_stack=[rows_level()], find="february")

        self.assertEqual(result["rows"], [])
        self.assertEqual(result["total_row_count"], 0)

    # @feature charts.drill-rows-reading
    def test_a_page_the_reader_turned_to_holds_the_rows_after_the_ones_before_it(self):
        _, chart, dashboard = self.make_content()
        alphabetical = [{"column": "description", "direction": "asc"}]

        with patch("insights.insights.doctype.insights_chart_v3.chart_drill.PAGE_SIZE", 2):
            first = self.drill(
                OWNER, chart.name, dashboard.name, drill_stack=[rows_level()], sort=alphabetical
            )
            second = self.drill(
                OWNER,
                chart.name,
                dashboard.name,
                drill_stack=[rows_level()],
                sort=alphabetical,
                page=2,
            )

        self.assertEqual(self.descriptions(first), sorted(OWNER_TODOS)[:2])
        self.assertEqual(self.descriptions(second), sorted(OWNER_TODOS)[2:])
        # the total counts the whole cut, so it is the same on every page
        self.assertEqual(second["total_row_count"], 3)

    # @feature charts.drill-rows-filter
    def test_a_filter_the_reader_wrote_narrows_the_rows_and_the_total_under_them(self):
        _, chart, dashboard = self.make_content()

        result = self.drill(
            OWNER,
            chart.name,
            dashboard.name,
            drill_stack=[rows_level()],
            row_filters=[rule("priority", "in", ["High"])],
        )

        self.assertEqual(self.descriptions(result), sorted([OPEN_HIGH, CLOSED_HIGH]))
        # the rule applies inside the cut, so the total counts only the rows it kept
        self.assertEqual(result["total_row_count"], 2)

    # @feature charts.drill-rows-filter charts.drill-rows-reading
    def test_the_filters_the_sort_the_find_and_the_page_all_hold_at_once(self):
        _, chart, dashboard = self.make_content()
        alphabetical = [{"column": "description", "direction": "asc"}]

        reading = {
            "row_filters": [rule("status", "=", "Open")],
            "find": "high",
            "sort": alphabetical,
        }
        narrowed = self.drill(OWNER, chart.name, dashboard.name, drill_stack=[rows_level()], **reading)

        # the status rule and the term both narrow: one open high todo is left
        self.assertEqual(self.descriptions(narrowed), [OPEN_HIGH])
        self.assertEqual(narrowed["total_row_count"], 1)

        # and the pages split the narrowed rows, not the whole segment
        with patch("insights.insights.doctype.insights_chart_v3.chart_drill.PAGE_SIZE", 1):
            first = self.drill(
                OWNER,
                chart.name,
                dashboard.name,
                drill_stack=[rows_level()],
                row_filters=[rule("priority", "=", "High")],
                sort=alphabetical,
            )
            second = self.drill(
                OWNER,
                chart.name,
                dashboard.name,
                drill_stack=[rows_level()],
                row_filters=[rule("priority", "=", "High")],
                sort=alphabetical,
                page=2,
            )

        self.assertEqual(self.descriptions(first), [CLOSED_HIGH])
        self.assertEqual(self.descriptions(second), [OPEN_HIGH])
        self.assertEqual(second["total_row_count"], 2)

    # @feature charts.drill-rows-filter
    def test_a_filter_offers_the_values_of_the_cut_it_narrows(self):
        _, chart, dashboard = self.make_content()

        with as_user(OWNER), db_connections():
            values = get_drill_rows_values(
                chart=chart.name,
                dashboard=dashboard.name,
                column="priority",
                drill_stack=[rows_level(filters=[equals("status", "Open")])],
            )

        # only values from the segment's rows: the closed todo's priority is not
        # listed, because picking it would leave the page empty
        self.assertEqual(sorted(values), ["High", "Low"])

    # @feature charts.drill-rows-filter dashboard.card-filter
    def test_a_filter_on_the_builder_grid_offers_the_cut_whatever_the_card_is_filtered_by(self):
        """`authoringDrillRows` sends the grid card's filters with every value
        list and range, as it does with the rows. A card filter applies after the
        chart's summarize, and the cut stops before it, so the value lists ignore
        it as the rows do."""
        query, chart, _ = self.make_content(operations=weighted_operations())
        level = rows_level(filters=[equals("status", "Open")])
        shape = {
            "query": query.name,
            "chart_type": chart.chart_type,
            "config": bar_config(),
            "chart_name": chart.name,
            "drill_stack": [level],
        }

        for card_filter in (rule("count_of_rows", ">", 0), rule("status", "=", "Closed")):
            with self.subTest(card_filter["column"]), as_user(OWNER), db_connections():
                values = get_authoring_drill_rows_values(
                    **shape, column="priority", card_filters=[card_filter]
                )
                weights = get_authoring_drill_rows_range(**shape, column="weight", card_filters=[card_filter])

                self.assertEqual(sorted(values), ["High", "Low"])
                self.assertEqual(weights, get_authoring_drill_rows_range(**shape, column="weight"))

    # @feature charts.drill-surface-bound
    def test_a_filter_on_a_column_that_is_not_on_the_surface_is_refused(self):
        _, chart, dashboard = self.make_content()

        for kwargs in (
            {"row_filters": [rule("password", "=", "x")]},
            {"row_filters": [rule("tabUser.password", "is_set", "")]},
        ):
            with self.assertRaises(frappe.ValidationError) as raised:
                self.drill(OWNER, chart.name, dashboard.name, drill_stack=[rows_level()], **kwargs)
            self.assertIn("is not a column", str(raised.exception))

        # a filter's value list is limited to the surface's columns too
        with as_user(OWNER), db_connections(), self.assertRaises(frappe.ValidationError):
            get_drill_rows_values(
                chart=chart.name,
                dashboard=dashboard.name,
                column="password",
                drill_stack=[rows_level()],
            )

    # @feature charts.drill-surface-bound
    def test_an_operator_the_engine_does_not_have_is_refused(self):
        _, chart, dashboard = self.make_content()

        with self.assertRaises(frappe.ValidationError) as raised:
            self.drill(
                OWNER,
                chart.name,
                dashboard.name,
                drill_stack=[rows_level()],
                row_filters=[rule("status", "matches", "Open")],
            )

        self.assertIn("is not supported", str(raised.exception))

    # @feature charts.drill-surface-bound
    def test_a_sort_on_a_column_that_is_not_on_the_surface_is_refused(self):
        _, chart, dashboard = self.make_content()

        with self.assertRaises(frappe.ValidationError):
            self.drill(
                OWNER,
                chart.name,
                dashboard.name,
                drill_stack=[rows_level()],
                sort=[{"column": "no_such_column", "direction": "asc"}],
            )

    # @feature charts.drill-surface-bound
    def test_a_direction_rows_cannot_run_in_is_refused(self):
        _, chart, dashboard = self.make_content()

        with self.assertRaises(frappe.ValidationError):
            self.drill(
                OWNER,
                chart.name,
                dashboard.name,
                drill_stack=[rows_level()],
                sort=[{"column": "description", "direction": "sideways"}],
            )

    # the order a breakdown comes back in
    #
    # One rule: a dimension with an order of its own is shown in that order, and
    # a dimension without one is ranked by the measure.

    # @feature charts.drill-breakdown
    def test_a_dimension_with_an_order_of_its_own_is_shown_in_it(self):
        _, chart, dashboard = self.timeline()

        result = self.drill(OWNER, chart.name, dashboard.name, drill_stack=[breakdown_level("date")])

        # a ranking would put February first and read as noise. A series reads
        # forwards, whatever the sizes along it
        self.assertEqual(self.buckets(result), TIMELINE_MONTHS)
        self.assertEqual([row["count_of_rows"] for row in result["rows"]], TIMELINE_COUNTS)

    # @feature charts.drill-breakdown
    def test_a_dimension_without_one_is_still_ranked_by_the_measure(self):
        _, chart, dashboard = self.timeline()

        result = self.drill(OWNER, chart.name, dashboard.name, drill_stack=[breakdown_level("priority")])

        # biggest first, which is the only reading a set of labels has
        self.assertEqual(
            [(row["priority"], row["count_of_rows"]) for row in result["rows"]],
            [("Low", 4), ("High", 2)],
        )

    # @feature charts.drill-breakdown
    def test_the_answer_says_which_way_its_rows_run_and_what_they_are_bucketed_by(self):
        _, chart, dashboard = self.timeline()

        ordered = self.drill(OWNER, chart.name, dashboard.name, drill_stack=[breakdown_level("date")])
        ranked = self.drill(OWNER, chart.name, dashboard.name, drill_stack=[breakdown_level("priority")])
        behind = self.drill(OWNER, chart.name, dashboard.name, drill_stack=[rows_level()])

        # the client draws by what it is told, never by a column type it guesses from
        self.assertEqual((ordered["ordered"], ordered["granularity"]), (True, "month"))
        self.assertEqual((ranked["ordered"], ranked["granularity"]), (False, None))
        self.assertEqual((behind["ordered"], behind["granularity"]), (False, None))

    # @feature charts.drill-additive
    def test_the_answer_says_whether_its_groups_add_up_to_the_segment_above_them(self):
        """A level read as parts of one whole rests on this, and the answer's own
        columns cannot supply it: nothing in a column of decimals says whether
        they hold sums or averages."""
        _, counted, dashboard = self.timeline()
        _, averaged, average_dashboard = self.timeline(config=bar_config(measures=[average()]))

        added = self.drill(OWNER, counted.name, dashboard.name, drill_stack=[breakdown_level("priority")])
        averages = self.drill(
            OWNER,
            averaged.name,
            average_dashboard.name,
            drill_stack=[breakdown_level("priority")],
        )
        behind = self.drill(OWNER, counted.name, dashboard.name, drill_stack=[rows_level()])

        self.assertTrue(added["additive"])
        # two groups' averages do not average, so these are not parts of anything
        self.assertFalse(averages["additive"])
        # a rows level groups nothing, so it has no groups to add
        self.assertFalse(behind["additive"])

    # @feature charts.drill-grain
    def test_the_grain_follows_the_span_of_the_segment_being_drilled(self):
        """A fixed default is arbitrary: one month of data is not ten years of it."""
        _, chart, dashboard = self.timeline()

        year = self.drill(OWNER, chart.name, dashboard.name, drill_stack=[breakdown_level("date")])
        february = self.drill(
            OWNER,
            chart.name,
            dashboard.name,
            drill_stack=[
                breakdown_level(
                    "date",
                    filters=[{"column": "description", "operator": "contains", "value": "february"}],
                )
            ],
        )

        # eleven months of fixtures read by the month. Three days of them by the day
        self.assertEqual(year["granularity"], "month")
        self.assertEqual(february["granularity"], "day")
        self.assertEqual(self.buckets(february), ["2024-02-15", "2024-02-16", "2024-02-17"])

    # @feature charts.drill-breakdown
    def test_an_ordered_breakdown_is_cut_to_its_most_recent_stretch(self):
        """Never a top-N by measure, which would take buckets out of the middle."""
        _, chart, dashboard = self.timeline()

        with patch("insights.insights.doctype.insights_chart_v3.chart_drill.BREAKDOWN_SIZE", 2):
            result = self.drill(
                OWNER,
                chart.name,
                dashboard.name,
                drill_stack=[breakdown_level("date", granularity="month")],
            )

        # the two most recent months, still forwards. A ranking would have kept
        # February, the biggest, and left a hole where June was
        self.assertEqual(self.buckets(result), TIMELINE_MONTHS[-2:])
        self.assertEqual(result["total_row_count"], len(TIMELINE_MONTHS))

    # @feature charts.drill-grain
    def test_a_grain_the_caller_names_outranks_the_derived_one(self):
        _, chart, dashboard = self.timeline()

        result = self.drill(
            OWNER,
            chart.name,
            dashboard.name,
            drill_stack=[breakdown_level("date", granularity="year")],
        )

        # the reader changed the grain on the level, so the span has no say
        self.assertEqual(result["granularity"], "year")
        self.assertEqual(self.buckets(result), ["2024-01-01"])
        self.assertEqual(result["rows"][0]["count_of_rows"], len(TIMELINE_TODOS))

    # @feature charts.drill-grain
    def test_a_grain_the_column_cannot_admit_is_refused(self):
        timed = [
            *todo_operations(TIMELINE_PREFIX),
            {"type": "cast", "column": {"type": "column", "column_name": "creation"}, "data_type": "Time"},
        ]
        dated = [
            *todo_operations(TIMELINE_PREFIX),
            {"type": "cast", "column": {"type": "column", "column_name": "creation"}, "data_type": "Date"},
        ]
        _, chart, dashboard = self.make_content()
        _, timed_chart, timed_dashboard = self.make_content(operations=timed)
        _, dated_chart, dated_dashboard = self.make_content(operations=dated)

        refused = (
            # a Time has no date part to take a month out of
            (timed_chart, timed_dashboard, breakdown_level("creation", granularity="month")),
            # and a Date has no time part to take an hour out of
            (dated_chart, dated_dashboard, breakdown_level("creation", granularity="hour")),
            # and a label has no order at all, so no grain can bucket it
            (chart, dashboard, breakdown_level("priority", granularity="month")),
            (chart, dashboard, breakdown_level("creation", granularity="fortnight")),
        )
        for on_chart, on_dashboard, level in refused:
            with self.assertRaises(frappe.ValidationError) as raised:
                self.drill(OWNER, on_chart.name, on_dashboard.name, drill_stack=[level])
            self.assertIn("cannot be broken down by", str(raised.exception))

    # @feature charts.drill-grain
    def test_a_time_column_is_bucketed_by_a_grain_it_has(self):
        """Hour, minute and second are all a column with no date part admits."""
        timed = [
            *todo_operations(),
            {"type": "cast", "column": {"type": "column", "column_name": "creation"}, "data_type": "Time"},
        ]
        _, chart, dashboard = self.make_content(operations=timed)

        result = self.drill(OWNER, chart.name, dashboard.name, drill_stack=[breakdown_level("creation")])

        self.assertTrue(result["ordered"])
        # the fixtures are created within one second, so the derivation floors on its finest grain
        self.assertEqual(result["granularity"], "second")

    # @feature charts.drill-number-card
    def test_a_number_cards_breakdown_carries_its_readings_and_not_its_targets(self):
        """A card names no measure when it is clicked, so the level keeps them all
        — all of them being what the card draws. A target is read off the card's
        own row, and broken down it is a column nobody clicked and an average
        that makes the whole level look like it does not add up."""
        _, chart, dashboard = self.make_content(chart_type="Number", config=number_config())

        result = self.drill(OWNER, chart.name, dashboard.name, drill_stack=[breakdown_level("priority")])

        self.assertEqual(self.column_names(result), ["priority", "Todos"])
        self.assertTrue(result["additive"])

    # @feature charts.drill-date-segment
    def test_a_level_under_a_time_bucket_is_filtered_by_the_clock_and_not_the_calendar(self):
        """A time of day read as a moment lands on today, and the bucket becomes a
        stretch of the calendar on a column that has no date part — which matches
        nothing, so the level under it looks empty."""
        timed = [
            *todo_operations(),
            {"type": "cast", "column": {"type": "column", "column_name": "creation"}, "data_type": "Time"},
        ]
        _, chart, dashboard = self.make_content(operations=timed)

        hours = self.drill(
            OWNER,
            chart.name,
            dashboard.name,
            drill_stack=[breakdown_level("creation", granularity="hour")],
        )
        # the fixtures are made in one go, so they share the hour they landed in
        self.assertEqual(len(hours["rows"]), 1)
        clicked = hours["rows"][0]["creation"]

        stack = [
            breakdown_level("creation", granularity="hour"),
            rows_level(filters=[equals("creation", clicked)]),
        ]
        behind = self.drill(OWNER, chart.name, dashboard.name, drill_stack=stack)
        self.assertEqual(behind["total_row_count"], len(OWNER_TODOS))

        # and the bucket it was narrowed by is an hour of the clock. A bound
        # carrying a date is one a store that does not coerce it away drops every
        # row for, and one carrying tomorrow's is a bucket nothing can be inside
        handed = self.drill(OWNER, chart.name, dashboard.name, drill_stack=stack, with_operations=True)
        bounds = [
            rule["value"]
            for operation in handed["operations"]
            if operation["type"] == "filter_group"
            for rule in operation["filters"]
            if rule["column"]["column_name"] == "creation"
        ]
        self.assertEqual(bounds[0], clicked)
        self.assertTrue(all(re.fullmatch(r"\d\d:\d\d:\d\d", bound) for bound in bounds), bounds)

    # @feature charts.drill-segment
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
            OWNER,
            chart.name,
            dashboard.name,
            drill_stack=[breakdown_level("priority", filters=[equals("status", "Open")], measure="Todos")],
        )

        self.assertEqual(self.column_names(result), ["priority", "Todos"])

    # @feature charts.drill-segment
    def test_segments_accumulate_down_the_stack(self):
        _, chart, dashboard = self.make_content()

        result = self.drill(
            OWNER,
            chart.name,
            dashboard.name,
            drill_stack=[
                breakdown_level("priority", filters=[equals("status", "Open")], measure="count_of_rows"),
                rows_level(filters=[equals("priority", "High")], measure="count_of_rows"),
            ],
        )

        # the status of the first level and the priority of the second, both
        self.assertEqual(self.descriptions(result), [OPEN_HIGH])

    # @feature charts.drill-rows
    def test_a_number_card_drills_on_an_empty_segment(self):
        _, chart, dashboard = self.make_content(
            chart_type="Number", config={"number_columns": [count("Todos")]}
        )

        result = self.drill(OWNER, chart.name, dashboard.name, drill_stack=[rows_level(measure="Todos")])

        self.assertEqual(self.descriptions(result), sorted(OWNER_TODOS))

    # @feature charts.drill-number-card
    def test_a_windowed_card_drills_into_the_window_it_reads(self):
        """A card holding one span against another draws only the first.

        The pipeline under it carries both, as the Or of every span the card
        fetches, so a click that pinned nothing came back with both months.
        """
        _, chart, dashboard = self.timeline(
            chart_type="Number",
            config={
                "number_columns": [count("Todos")],
                "date_column": dimension("date", "Date"),
                # anchored, so the span the card reads is the fixtures' February
                "window": {"span": "current month", "anchor": "2024-02-15"},
                "number_column_options": [{"comparison": {"source": "previous"}}],
            },
        )

        result = self.drill(
            OWNER,
            chart.name,
            dashboard.name,
            drill_stack=[rows_level(filters=[equals("date", TIMELINE_MONTHS[1])], measure="Todos")],
        )

        # February alone: January is in the pipeline only because the card
        # compares against it
        self.assertEqual(self.descriptions(result), FEBRUARY)

    # @feature charts.drill-number-card
    def test_a_card_whose_span_has_moved_refuses_the_drill(self):
        """Spans are stored unresolved, so a moving span starts on a different
        day tomorrow. A drill from the old start day would return one day of rows
        as if they were the whole span."""
        _, chart, dashboard = self.timeline(
            chart_type="Number",
            config={
                "number_columns": [count("Todos")],
                "date_column": dimension("date", "Date"),
                "window": {"span": "current month", "anchor": "2024-02-15"},
            },
        )

        with self.assertRaises(frappe.ValidationError):
            self.drill(
                OWNER,
                chart.name,
                dashboard.name,
                drill_stack=[rows_level(filters=[equals("date", "2023-11-01")], measure="Todos")],
            )

    # @feature charts.drill-number-card
    def test_a_span_that_runs_to_its_anchor_drills_to_the_day_the_card_was_read(self):
        """`month to date` runs from the first of the month to its anchor. The
        start stays fixed, but the end moves every night. A card read on the
        16th and clicked on the 17th must not return the 17th's rows."""
        _, chart, dashboard = self.timeline(
            chart_type="Number",
            config={
                "number_columns": [count("Todos")],
                "date_column": dimension("date", "Date"),
                # no anchor: the shape `setDateColumn` writes when an author
                # picks a date column
                "window": {"span": "month to date"},
            },
        )

        with patch("insights.insights.query_builders.sql_functions.nowdate", return_value="2024-02-17"):
            drawn = frappe.get_doc(DT.CHART, chart.name).fetch(force=True)
            clicked_the_next_day = self.drill(
                OWNER,
                chart.name,
                dashboard.name,
                drill_stack=[
                    rows_level(
                        filters=[equals("date", "2024-02-01")],
                        measure="Todos",
                        drawn_on="2024-02-16",
                    )
                ],
            )

        # the card the reader is looking at was read on the 16th, so it counted
        # the 15th and the 16th and not the 17th
        self.assertEqual(drawn["drawn_on"], "2024-02-17")
        self.assertEqual(
            self.descriptions(clicked_the_next_day),
            sorted(d for d, (date, _) in TIMELINE_TODOS.items() if date in ("2024-02-15", "2024-02-16")),
        )

    # @feature charts.drill-number-card
    def test_a_span_that_moved_overnight_drills_to_the_whole_span_the_card_counted(self):
        """`ChartDrillDown.vue` sends the day the card was read as `drawn_on` on
        every level. The card's span filter is inside the cut. Resolved against
        the day of the click, it is next month: a click on 1 March on a card read
        on 17 February filtered February's rows by March and found nothing."""
        _, chart, dashboard = self.timeline(
            chart_type="Number",
            config={
                "number_columns": [count("Todos")],
                "date_column": dimension("date", "Date"),
                "window": {"span": "current month"},
            },
        )

        with patch("insights.insights.query_builders.sql_functions.nowdate", return_value="2024-03-01"):
            clicked_next_month = self.drill(
                OWNER,
                chart.name,
                dashboard.name,
                drill_stack=[
                    rows_level(
                        filters=[equals("date", "2024-02-01")],
                        measure="Todos",
                        drawn_on="2024-02-17",
                    )
                ],
            )

        self.assertEqual(self.descriptions(clicked_next_month), FEBRUARY)

    # @feature charts.drill-number-card charts.drill-rows
    def test_the_builders_rows_level_is_read_for_the_day_the_card_was(self):
        """The builder (`authoring.get_drill_data`) and a View
        (`view.get_drill_data`) return the same rows for the same click and
        `drawn_on`."""
        config = {
            "number_columns": [count("Todos")],
            "date_column": dimension("date", "Date"),
            "window": {"span": "current month"},
        }
        query, chart, dashboard = self.timeline(chart_type="Number", config=config)
        level = rows_level(filters=[equals("date", "2024-02-01")], measure="Todos", drawn_on="2024-02-17")

        with patch("insights.insights.query_builders.sql_functions.nowdate", return_value="2024-03-01"):
            with as_user(OWNER), db_connections():
                built = get_authoring_drill_data(
                    query=query.name,
                    chart_type="Number",
                    config=config,
                    chart_name=chart.name,
                    drill_stack=[level],
                )
                read = get_drill_data(chart=chart.name, dashboard=dashboard.name, drill_stack=[level])

        self.assertEqual(self.descriptions(built), FEBRUARY)
        self.assertEqual(self.descriptions(read), FEBRUARY)

    # @feature charts.drill-number-card dashboard.drill
    def test_a_level_opened_as_a_query_holds_the_rows_the_dialog_showed(self):
        """`AuthoringDrillDown.vue` saves the returned `operations` as a new
        query in the workbook. That query runs on the day it is opened, outside
        any dashboard. So its steps must carry the card's day and the grid's
        filters, or it returns other rows or none."""
        config = {
            "number_columns": [count("Todos")],
            "date_column": dimension("date", "Date"),
            "window": {"span": "current month"},
        }
        query, chart, dashboard = self.timeline(chart_type="Number", config=config)
        february_t = sorted(d for d in FEBRUARY if "february t" in d)

        for action in ({"rows": True, "measure": "Todos"}, {"breakdown": "priority", "measure": "Todos"}):
            with self.subTest(next(iter(action))):
                level = {
                    **rows_level(filters=[equals("date", "2024-02-01")], drawn_on="2024-02-17"),
                    "action": action,
                }
                with as_user(OWNER), db_connections():
                    shown = get_authoring_drill_data(
                        query=query.name,
                        chart_type="Number",
                        config=config,
                        chart_name=chart.name,
                        dashboard_items=frappe.parse_json(
                            frappe.db.get_value(DT.DASHBOARD, dashboard.name, "items")
                        ),
                        filters={"Description": {"operator": "contains", "value": "february t"}},
                        drill_stack=[level],
                    )

                with patch(
                    "insights.insights.query_builders.sql_functions.nowdate", return_value="2024-03-01"
                ):
                    with as_user(OWNER), db_connections():
                        opened = frappe.get_doc(
                            {
                                "doctype": DT.QUERY,
                                "title": "Drill API Test Opened Query",
                                "workbook": query.workbook,
                                "use_live_connection": 1,
                                "is_builder_query": 1,
                                "operations": shown["operations"],
                            }
                        ).insert()
                        rows = opened.execute(force=True)["rows"]

                self.assertEqual(rows, shown["rows"])
                if "rows" in action:
                    self.assertEqual(self.descriptions(shown), february_t)

    # @feature charts.drill-open-as-query dashboard.drill
    def test_a_level_opened_as_a_query_names_each_dashboard_filter_it_could_not_carry(self):
        """`AuthoringDrillDown.vue` lists them in its toast. A filter linked to a
        source query of the chart's query narrowed the dialog's rows, but the
        opened query has no step to hold it. A filter linked to the chart's own
        query becomes a step and is not listed."""
        source, chart, _ = self.make_content()
        with as_user(OWNER):
            query = frappe.get_doc(
                {
                    "doctype": DT.QUERY,
                    "title": "Drill API Test Reading Query",
                    "workbook": source.workbook,
                    "use_live_connection": 1,
                    "is_builder_query": 1,
                    "operations": [{"type": "source", "table": {"type": "query", "query_name": source.name}}],
                }
            ).insert()
        chart.db_set("query", query.name, update_modified=False)
        items = [
            {"type": "chart", "chart": chart.name},
            {
                "type": "filter",
                "filter_name": "Description",
                "links": {chart.name: f"`{source.name}`.`description`"},
            },
            {"type": "filter", "filter_name": "Status", "links": {chart.name: f"`{query.name}`.`status`"}},
        ]

        with as_user(OWNER), db_connections():
            shown = get_authoring_drill_data(
                query=query.name,
                chart_type=chart.chart_type,
                config=frappe.parse_json(chart.config),
                chart_name=chart.name,
                dashboard_items=items,
                filters={
                    "Description": {"operator": "contains", "value": TODO_PREFIX},
                    "Status": {"operator": "=", "value": "Open"},
                },
                drill_stack=[rows_level(filters=[equals("priority", "High")], measure="count_of_rows")],
            )

        self.assertEqual(shown["uncarried_filters"], ["Description"])
        self.assertIn(
            "status",
            [rule["column"]["column_name"] for rule in shown["operations"][1].get("filters") or []],
        )

    # @feature charts.drill-number-card dashboard.drill
    def test_a_dashboard_filter_over_a_span_is_read_for_the_day_the_card_was(self):
        """The drill routes the dashboard's `within` filter as the card does.
        Resolved against the day of the click, it meant next month, and a drill
        on a card read in February found nothing."""
        query, chart, _ = self.timeline(
            chart_type="Number",
            config={
                "number_columns": [count("Todos")],
                "date_column": dimension("date", "Date"),
                "window": {"span": "current month"},
            },
        )
        this_month = {
            query.name: {
                "type": "filter_group",
                "logical_operator": "And",
                "filters": [
                    {
                        "type": "filter",
                        "column": {"type": "column", "column_name": "date"},
                        "operator": "within",
                        "value": {"span": "current month"},
                    }
                ],
            }
        }
        level = rows_level(filters=[equals("date", "2024-02-01")], measure="Todos", drawn_on="2024-02-17")

        with patch("insights.insights.query_builders.sql_functions.nowdate", return_value="2024-03-01"):
            with as_user(OWNER), db_connections():
                clicked_next_month = drill_data(chart, [level], adhoc_filters=this_month)

        self.assertEqual(self.descriptions(clicked_next_month), FEBRUARY)

    # @feature charts.drill-number-card dashboard.drill
    def test_a_card_whose_author_pinned_its_span_names_the_day_it_was_read(self):
        """The pinned span never moves, but the dashboard's filters resolve
        against the day of the read. The drill resolves them against the
        `drawn_on` it is sent, so the card must return it."""
        _, chart, dashboard = self.timeline(
            chart_type="Number",
            config={
                "number_columns": [count("Todos")],
                "date_column": dimension("date", "Date"),
                "window": {"span": "current month", "anchor": "2024-02-15"},
            },
        )

        with patch("insights.insights.query_builders.sql_functions.nowdate", return_value="2024-03-01"):
            with as_user(OWNER), db_connections():
                card = get_chart_data(chart=chart.name, dashboard=dashboard.name, force=True)

        self.assertEqual(card["drawn_on"], "2024-03-01")

    # @feature charts.drill-number-card
    def test_a_span_in_the_source_query_is_read_for_the_day_the_card_was(self):
        """The query's own `within` filter resolves when the query builds,
        before any operation of the chart."""
        this_month = {
            "type": "filter",
            "column": {"type": "column", "column_name": "date"},
            "operator": "within",
            "value": {"span": "current month"},
        }
        _, chart, _ = self.make_content(
            operations=[*todo_operations(TIMELINE_PREFIX), this_month],
            chart_type="Number",
            config={"number_columns": [count("Todos")], "date_column": dimension("date", "Date")},
        )
        level = rows_level(measure="Todos", drawn_on="2024-02-17")

        with patch("insights.insights.query_builders.sql_functions.nowdate", return_value="2024-03-01"):
            with as_user(OWNER), db_connections():
                clicked_next_month = drill_data(chart, [level])

        self.assertEqual(self.descriptions(clicked_next_month), FEBRUARY)

    # @feature charts.drill-number-card
    def test_a_card_grouped_by_a_grain_drills_into_the_period_it_reads(self):
        """A grain filters nothing, so the whole table is under the reading."""
        _, chart, dashboard = self.timeline(
            chart_type="Number",
            config={
                "number_columns": [count("Todos")],
                "date_column": dimension("date", "Date"),
                "window": {"grain": "month"},
            },
        )

        result = self.drill(
            OWNER,
            chart.name,
            dashboard.name,
            # the newest bucket, which is the one the card reads
            drill_stack=[rows_level(filters=[equals("date", TIMELINE_MONTHS[-1])], measure="Todos")],
        )

        self.assertEqual(self.descriptions(result), [f"{TIMELINE_PREFIX} december"])

    # @feature charts.drill-conditional-measure
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

        result = self.drill(OWNER, chart.name, dashboard.name, drill_stack=[rows_level(measure="Open")])

        # the rows behind the number are the ones the measure counted
        self.assertEqual(self.descriptions(result), sorted([OPEN_HIGH, OPEN_LOW]))

    # a segment the chart spread across its columns

    # @feature charts.drill-segment
    def test_a_pivot_cell_pins_the_row_and_the_column(self):
        _, chart, dashboard = self.make_content(chart_type="Table", config=pivot_config())

        result = self.drill(
            OWNER,
            chart.name,
            dashboard.name,
            # the cell under the "High" column, on the "Open" row: the row
            # dimension and the column dimension pin together
            drill_stack=[
                rows_level(filters=[equals("status", "Open"), equals("priority", "High")], measure="Todos")
            ],
        )

        self.assertEqual(self.descriptions(result), [OPEN_HIGH])

    # @feature charts.drill-segment
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
            OWNER,
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

    # @feature charts.drill-segment
    def test_an_others_slice_of_a_split_refuses_the_drill(self):
        """A split keeps its top values and relabels the rest `Others` after the
        point where the drill cuts. A cut on `Others` matched no row, and the
        dialog showed an empty grid with no reason."""
        _, chart, dashboard = self.make_content(
            chart_type="Bar",
            config={
                "limit": 50,
                "x_axis": {"dimension": dimension("status")},
                "split_by": {"dimension": dimension("priority"), "max_split_values": 1},
                "y_axis": {"series": [{"measure": count("Todos")}]},
                "order_by": [],
            },
        )

        with self.assertRaises(frappe.ValidationError):
            self.drill(
                OWNER,
                chart.name,
                dashboard.name,
                drill_stack=[rows_level(filters=[equals("status", "Open"), equals("priority", "Others")])],
            )

    # @feature charts.drill-segment
    def test_a_split_that_really_holds_others_drills_into_it(self):
        """The engine writes the label only when it cuts values off a single
        split column. A split with fewer values than the cap is not relabelled,
        so an `Others` series here has real rows behind it."""
        _, chart, dashboard = self.make_content(
            chart_type="Bar",
            operations=bucketed_operations(),
            config={
                "limit": 50,
                "x_axis": {"dimension": dimension("status")},
                "split_by": {"dimension": dimension("bucket"), "max_split_values": 10},
                "y_axis": {"series": [{"measure": count("Todos")}]},
                "order_by": [],
            },
        )

        result = self.drill(
            OWNER,
            chart.name,
            dashboard.name,
            drill_stack=[rows_level(filters=[equals("status", "Open"), equals("bucket", "Others")])],
        )

        self.assertEqual(self.descriptions(result), sorted([OPEN_HIGH, OPEN_LOW]))

    # @feature charts.drill-segment
    def test_a_split_that_cut_a_tail_onto_a_real_others_refuses_the_drill(self):
        """A real `Others` value keeps its name, and the cut-off values are
        relabelled `Others` too, so both show as one series. A cut on the label
        finds only the real rows and would show their count as the whole bar's."""
        _, chart, dashboard = self.make_content(
            chart_type="Bar",
            operations=half_others_operations(),
            config={
                "limit": 50,
                "x_axis": {"dimension": dimension("status")},
                # the two High todos rank first as `Others`, so `Low` is the tail
                "split_by": {"dimension": dimension("bucket"), "max_split_values": 1},
                "y_axis": {"series": [{"measure": count("Todos")}]},
                "order_by": [],
            },
        )

        with self.assertRaises(frappe.ValidationError):
            self.drill(
                OWNER,
                chart.name,
                dashboard.name,
                drill_stack=[rows_level(filters=[equals("bucket", "Others")])],
            )

    # @feature charts.drill-segment
    def test_a_second_split_column_leaves_others_meaning_itself(self):
        """The engine relabels values only for a single split column. With two
        split columns nothing is relabelled, so an `Others` value is real."""
        _, chart, dashboard = self.make_content(
            chart_type="Table",
            operations=bucketed_operations(),
            config={
                "limit": 50,
                "rows": [dimension("status")],
                "columns": [dimension("bucket"), dimension("priority")],
                "values": [count()],
                "order_by": [],
            },
        )

        result = self.drill(
            OWNER,
            chart.name,
            dashboard.name,
            drill_stack=[rows_level(filters=[equals("status", "Open"), equals("bucket", "Others")])],
        )

        self.assertEqual(self.descriptions(result), sorted([OPEN_HIGH, OPEN_LOW]))

    # @feature charts.drill-date-segment
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
            OWNER,
            chart.name,
            dashboard.name,
            drill_stack=[rows_level(filters=[equals("creation", str(this_month))])],
        )
        empty = self.drill(
            OWNER,
            chart.name,
            dashboard.name,
            drill_stack=[
                rows_level(filters=[equals("creation", str(frappe.utils.add_months(this_month, -1)))])
            ],
        )

        self.assertEqual(self.descriptions(rows), sorted(OWNER_TODOS))
        self.assertEqual(empty["rows"], [])

    # The chart's own operation is not the only thing that buckets a date: a
    # breakdown level groups one at a grain of its own, and a click on one of
    # those bars pins a bucket no operation of the chart has ever heard of.

    # @feature charts.drill-date-segment
    def test_a_bucket_a_level_made_is_drilled_as_the_span_it_covers(self):
        _, chart, dashboard = self.timeline()

        result = self.drill(
            OWNER,
            chart.name,
            dashboard.name,
            drill_stack=[
                breakdown_level("date", granularity="month"),
                rows_level(filters=[equals("date", TIMELINE_MONTHS[1])]),
            ],
        )

        # the whole month, not the instant its first bucket starts at
        self.assertEqual(self.descriptions(result), FEBRUARY)

    # @feature charts.drill-date-segment
    def test_a_bucket_a_level_made_narrows_the_level_below_it(self):
        _, chart, dashboard = self.timeline()

        result = self.drill(
            OWNER,
            chart.name,
            dashboard.name,
            drill_stack=[
                breakdown_level("date", granularity="month"),
                breakdown_level("priority", filters=[equals("date", TIMELINE_MONTHS[1])]),
            ],
        )

        self.assertEqual(
            sorted((row["priority"], row["count_of_rows"]) for row in result["rows"]),
            [("High", 1), ("Low", 2)],
        )

    # @feature charts.drill-date-segment
    def test_a_bucket_made_under_a_categorical_level_is_still_a_span(self):
        _, chart, dashboard = self.timeline()

        result = self.drill(
            OWNER,
            chart.name,
            dashboard.name,
            drill_stack=[
                breakdown_level("priority"),
                breakdown_level("date", filters=[equals("priority", "Low")], granularity="month"),
                rows_level(filters=[equals("date", TIMELINE_MONTHS[1])]),
            ],
        )

        # both segments hold: the priority the first level pinned, and the whole
        # month the second one bucketed
        self.assertEqual(self.descriptions(result), FEBRUARY_LOW)

    # @feature charts.drill-date-segment
    def test_a_level_that_names_no_grain_pins_the_value_it_was_given(self):
        """A caller with no answer to echo yet, or one that never echoes."""
        _, chart, dashboard = self.timeline()

        result = self.drill(
            OWNER,
            chart.name,
            dashboard.name,
            drill_stack=[
                breakdown_level("date"),
                rows_level(filters=[equals("date", "2024-02-15")]),
            ],
        )

        self.assertEqual(self.descriptions(result), [f"{TIMELINE_PREFIX} february one"])

    # @feature charts.drill-grain
    def test_a_grain_an_earlier_level_cannot_admit_is_refused(self):
        _, chart, dashboard = self.timeline()

        with self.assertRaises(frappe.ValidationError) as raised:
            self.drill(
                OWNER,
                chart.name,
                dashboard.name,
                drill_stack=[
                    breakdown_level("date", granularity="fortnight"),
                    rows_level(filters=[equals("date", TIMELINE_MONTHS[1])]),
                ],
            )

        self.assertIn("cannot be broken down by", str(raised.exception))

    # the wire cannot widen what the chart exposes

    # @feature charts.drill-surface-bound
    def test_a_column_that_is_not_on_the_surface_is_refused(self):
        _, chart, dashboard = self.make_content()

        for stack in (
            [rows_level(filters=[equals("tabUser.password", "x")])],
            [breakdown_level("password")],
        ):
            with self.assertRaises(frappe.ValidationError) as raised:
                self.drill(OWNER, chart.name, dashboard.name, drill_stack=stack)
            self.assertIn("is not a column", str(raised.exception))

    # @feature charts.drill-surface-bound
    def test_no_drill_response_carries_the_query_behind_the_chart(self):
        query, chart, dashboard = self.make_content()

        result = self.drill(
            OWNER,
            chart.name,
            dashboard.name,
            drill_stack=[rows_level(filters=[equals("status", "Open")])],
        )

        serialized = json.dumps(result, default=str)
        for leak in ("operations", "raw_sql", "tabToDo", query.name):
            self.assertNotIn(leak, serialized, f"{leak} must not reach a reader")
        self.assertNotIn("sql", result)

    # what the menu offers before anything is clicked

    # @feature charts.drill-breakdown-offers
    def test_the_chart_offers_the_dimensions_of_the_pre_summarize_surface(self):
        _, chart, _ = self.make_content()

        with as_user(OWNER), db_connections():
            dimensions = {d["name"]: d["type"] for d in drill_dimensions(chart)}
        # the surface underneath the summarize, so a column the chart does not
        # draw is still a candidate
        self.assertEqual(dimensions.get("priority"), "String")
        self.assertEqual(dimensions.get("status"), "String")
        self.assertEqual(dimensions.get("creation"), "Datetime")
        # what the summarize produced is not on the surface it summarized
        self.assertNotIn("count_of_rows", dimensions)
        # and neither is anything that measures rather than groups
        self.assertNotIn("docstatus", dimensions)

    # @feature charts.drill-record-link
    def test_a_drilled_row_names_the_desk_record_it_opens(self):
        _, chart, dashboard = self.make_content()

        result = self.drill(
            OWNER,
            chart.name,
            dashboard.name,
            drill_stack=[rows_level(filters=[equals("status", "Open")])],
        )

        # the row's own document, and the Link fields beside it on the same row
        self.assertEqual(result["record_links"]["name"], "ToDo")
        self.assertEqual(result["record_links"]["allocated_to"], "User")

    # @feature charts.drill-record-link
    def test_a_renamed_name_column_still_names_the_record(self):
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
            OWNER,
            chart.name,
            dashboard.name,
            drill_stack=[rows_level(filters=[equals("status", "Open")])],
        )

        # a rename says what the column is called, not what it holds, so the link
        # follows it rather than giving up on it
        self.assertEqual(result["record_links"]["todo_id"], "ToDo")
        self.assertNotIn("name", result["record_links"])

    # @feature charts.drill-record-link
    def test_a_dropped_name_column_carries_no_record_link(self):
        dropped = [
            *todo_operations(),
            {"type": "select", "column_names": ["status", "priority"]},
        ]
        _, chart, dashboard = self.make_content(operations=dropped)

        result = self.drill(
            OWNER,
            chart.name,
            dashboard.name,
            drill_stack=[rows_level(filters=[equals("status", "Open")])],
        )

        # nothing on the row names a document, so the client is told nothing
        # rather than told a document that might be the wrong one
        self.assertNotIn("record_links", result)

    # @feature charts.drill-record-link
    def test_a_child_row_does_not_name_itself(self):
        _, chart, dashboard = self.make_content(
            operations=has_role_operations(),
            config=bar_config_over("parenttype"),
        )

        result = self.drill(
            OWNER,
            chart.name,
            dashboard.name,
            drill_stack=[rows_level(filters=[equals("parenttype", "User")])],
        )

        # a child row has no form of its own — the desk routes the parent, which
        # the row cannot name. The Link fields beside it still name theirs
        self.assertNotIn("name", result["record_links"])
        self.assertEqual(result["record_links"]["role"], "Role")

    # @feature charts.drill-record-link
    def test_only_a_rows_level_carries_record_links(self):
        _, chart, dashboard = self.make_content()

        result = self.drill(
            OWNER,
            chart.name,
            dashboard.name,
            drill_stack=[breakdown_level("priority", filters=[equals("status", "Open")])],
        )

        self.assertNotIn("record_links", result)

    # dashboard filters

    # @feature dashboard.drill
    def test_dashboard_filter_state_reaches_the_drill(self):
        _, chart, dashboard = self.make_content()

        result = self.drill(
            OWNER,
            chart.name,
            dashboard.name,
            filters={"Description": {"operator": "contains", "value": "open low"}},
            drill_stack=[rows_level(filters=[equals("status", "Open")])],
        )

        # the rows agree with the number the filtered card was showing
        self.assertEqual(self.descriptions(result), [OPEN_LOW])

    # @feature charts.drill-surface-bound
    def test_a_chart_keyed_filter_group_does_not_reach_the_drill(self):
        """A card filter lands after the chart's summarize, where the drill does not go."""
        query, chart, _ = self.make_content()

        adhoc_filters = {
            # a rule on the card's own measure. The drill's pipeline is cut
            # before the summarize, so applying it there would throw
            chart.name: filter_group("count_of_rows", ">", 5),
            query.name: filter_group("description", "contains", "open low"),
        }

        with as_user(OWNER), db_connections():
            result = drill_data(
                chart,
                [rows_level(filters=[equals("status", "Open")])],
                adhoc_filters=adhoc_filters,
            )

        # the query-keyed group still narrows the rows
        self.assertEqual(self.descriptions(result), [OPEN_LOW])

    # who may drill, through `insights.api.view`

    def view_drill(self, user, chart, dashboard, **kwargs):
        with as_user(user), db_connections():
            return get_drill_data(chart=chart, dashboard=dashboard, **kwargs)

    # @feature charts.drill-changed-chart
    def test_a_drill_from_a_chart_that_changed_since_it_was_drawn_is_refused(self):
        """`ChartDrillDown.vue` sends the `modified` of the chart the card
        rendered. A card keeps its result until Refresh, so a drill after someone
        else's edit would cut a chart the card does not show."""
        _, chart, dashboard = self.make_content(run_as_owner=0)
        drawn = str(chart.modified)
        level = {**breakdown_level("status"), "modified": drawn}

        def drill():
            with as_user(OWNER), db_connections():
                return get_drill_data(chart=chart.name, dashboard=dashboard.name, drill_stack=[level])

        self.assertTrue(drill()["rows"])

        with as_user(OWNER):
            edited = frappe.get_doc(DT.CHART, chart.name)
            edited.title = "Drill API Test Chart, edited"
            edited.save()

        with self.assertRaisesRegex(frappe.ValidationError, "This chart changed. Refresh to drill."):
            drill()

    # @feature charts.drill-changed-chart
    def test_a_drill_after_an_edit_to_a_query_the_chart_reads_is_refused(self):
        """`ChartDrillDown.vue` sends the `modified` that `view.get_chart_data`
        returned with the card's rows. The drill cuts the queries as they are
        now, so an edit to the chart's query, or to a query it reads, would cut
        new rows under the old number."""
        query, chart, dashboard = self.make_content(run_as_owner=0)
        with as_user(OWNER):
            inner = frappe.get_doc(
                {
                    "doctype": DT.QUERY,
                    "title": "Drill API Test Inner Query",
                    "workbook": query.workbook,
                    "use_live_connection": 1,
                    "is_builder_query": 1,
                    "operations": todo_operations(),
                }
            ).insert()
            query.operations = frappe.as_json(
                [{"type": "source", "table": {"type": "query", "query_name": inner.name}}]
            )
            query.save()

        def drill():
            with as_user(OWNER), db_connections():
                drawn = get_chart_data(chart=chart.name, dashboard=dashboard.name)["chart"]["modified"]
            level = {**breakdown_level("status"), "modified": drawn}

            def again():
                with as_user(OWNER), db_connections():
                    return get_drill_data(chart=chart.name, dashboard=dashboard.name, drill_stack=[level])

            return again

        for hops, edited in (("two hops", inner.name), ("one hop", query.name)):
            with self.subTest(hops):
                drawn_before = drill()
                self.assertTrue(drawn_before()["rows"])

                with as_user(OWNER):
                    doc = frappe.get_doc(DT.QUERY, edited)
                    doc.title = f"{doc.title}, edited"
                    doc.save()

                with self.assertRaisesRegex(frappe.ValidationError, "This chart changed. Refresh to drill."):
                    drawn_before()
                # a card read after the edit can drill
                self.assertTrue(drill()()["rows"])

    # @feature charts.drill-changed-chart
    def test_a_query_saved_while_the_card_is_read_leaves_the_card_the_version_before_it(self):
        """A save between reading the rows and returning them would pair the old
        rows with the new `modified`. The drill would then cut the edited query
        under the old number."""
        query, chart, dashboard = self.make_content(run_as_owner=0)
        read_rows = InsightsChartv3.fetch

        def saved_while_read(doc, *args, **kwargs):
            result = read_rows(doc, *args, **kwargs)
            edited = frappe.get_doc(DT.QUERY, query.name)
            edited.title = f"{edited.title}, edited"
            edited.save()
            return result

        with patch.object(InsightsChartv3, "fetch", saved_while_read), as_user(OWNER), db_connections():
            drawn = get_chart_data(chart=chart.name, dashboard=dashboard.name, force=True)["chart"][
                "modified"
            ]

        level = {**breakdown_level("status"), "modified": drawn}
        with self.assertRaisesRegex(frappe.ValidationError, "This chart changed. Refresh to drill."):
            self.view_drill(OWNER, chart.name, dashboard.name, drill_stack=[level])

    # @feature charts.drill-changed-chart charts.preview
    def test_a_builder_drill_after_a_teammates_save_is_refused(self):
        """`chart_preview.ts` sends the `modified` from `authoring.get_chart_data`
        on every level. The builder drills the config it sends and the stored
        queries under it, so a save to either query or to the chart would cut
        new rows under the old number. The author's unsaved config is not checked."""
        query, chart, _ = self.make_content(run_as_owner=0)
        with as_user(OWNER):
            inner = frappe.get_doc(
                {
                    "doctype": DT.QUERY,
                    "title": "Drill API Test Inner Query",
                    "workbook": query.workbook,
                    "use_live_connection": 1,
                    "is_builder_query": 1,
                    "operations": todo_operations(),
                }
            ).insert()
            query.operations = frappe.as_json(
                [{"type": "source", "table": {"type": "query", "query_name": inner.name}}]
            )
            query.save()
        shape = {"query": query.name, "chart_type": chart.chart_type, "chart_name": chart.name}

        def card():
            with as_user(OWNER), db_connections():
                return get_authoring_chart_data(**shape, config=bar_config(), force=True)["modified"]

        def drill(drawn, config=None):
            level = {**breakdown_level("status"), "modified": drawn}
            with as_user(OWNER), db_connections():
                return get_authoring_drill_data(**shape, config=config or bar_config(), drill_stack=[level])

        self.assertTrue(drill(card(), {**bar_config(), "limit": 5})["rows"])

        for edited in (DT.QUERY, inner.name), (DT.QUERY, query.name), (DT.CHART, chart.name):
            with self.subTest(edited):
                drawn = card()
                with as_user(OWNER):
                    doc = frappe.get_doc(*edited)
                    doc.title = f"{doc.title}, edited"
                    doc.save()

                with self.assertRaisesRegex(frappe.ValidationError, "This chart changed. Refresh to drill."):
                    drill(drawn)
                self.assertTrue(drill(card())["rows"])

    def share_dashboard_with(self, dashboard, user):
        """Give `user` their own grant: a DocShare, which needs no role."""
        frappe.share.add(DT.DASHBOARD, dashboard, user=user, read=1, notify=0)

    # @feature charts.drill-breakdown charts.drill-rows charts.drill-rows-export permissions.chart-run-as-owner
    def test_a_chart_run_as_its_owner_offers_another_reader_only_what_the_owner_saved(self):
        """With `run_as_owner` set, a reader with their own grant still reads the
        owner's rows. A breakdown, the rows and the file would each give out more
        than the owner saved. The owner keeps all three."""
        _, chart, dashboard = self.make_content(run_as_owner=1)
        self.share_dashboard_with(dashboard.name, OUTSIDER)

        with as_user(OUTSIDER), db_connections():
            card = get_chart_data(chart=chart.name, dashboard=dashboard.name)
        self.assertEqual(card["drill"], {"dimensions": [], "can_rows": False})

        for level in (breakdown_level("priority"), rows_level()):
            answer = self.view_drill(OUTSIDER, chart.name, dashboard.name, drill_stack=[level])
            self.assertEqual(answer["rows"], [])
            self.assertIn("not_permitted", answer)
        with self.assertRaises(frappe.PermissionError):
            self.view_export(OUTSIDER, chart.name, dashboard.name, drill_stack=[rows_level()])

        with as_user(OWNER), db_connections():
            card = get_chart_data(chart=chart.name, dashboard=dashboard.name)
        self.assertTrue(card["drill"]["dimensions"])
        self.assertTrue(card["drill"]["can_rows"])
        broken_down = self.view_drill(
            OWNER, chart.name, dashboard.name, drill_stack=[breakdown_level("priority")]
        )
        self.assertTrue(broken_down["rows"])

    # @feature dashboard.card-filter permissions.chart-run-as-owner
    def test_a_chart_run_as_its_owner_takes_only_the_owners_dashboard_filters(self):
        """A reader's own card filter slices the owner's rows another way, as a
        breakdown does. A dashboard filter the owner linked only narrows the
        chart the owner saved. `view.get_card_values` follows the same rule."""
        from insights.api.view import get_card_values

        _, chart, dashboard = self.make_content(run_as_owner=1)
        self.share_dashboard_with(dashboard.name, OUTSIDER)
        own_filter = [{"column": "status", "operator": "=", "value": "Open"}]
        owners_filter = {"Description": {"operator": "=", "value": OPEN_HIGH}}

        def read(user, **kwargs):
            with as_user(user), db_connections():
                card = get_chart_data(chart=chart.name, dashboard=dashboard.name, force=True, **kwargs)
                values = get_card_values(chart=chart.name, column="status", dashboard=dashboard.name)
            return card, values

        card, values = read(OUTSIDER, card_filters=own_filter)
        self.assertEqual(card["rows"], [])
        self.assertIn("not_permitted", card)
        self.assertEqual(values, [])

        card, _ = read(OUTSIDER, filters=owners_filter)
        self.assertEqual([row["status"] for row in card["rows"]], ["Open"])

        card, values = read(OWNER, card_filters=own_filter)
        self.assertEqual([row["status"] for row in card["rows"]], ["Open"])
        self.assertEqual(sorted(values), ["Closed", "Open"])

    # @feature dashboard.card-filter permissions.chart-run-as-owner
    def test_a_card_says_whether_its_reader_may_filter_it(self):
        """`useChartCell` reads `can_filter` to show a table card's filter. The
        server refuses a reader's own filter on a chart run as its owner, so the
        card must not show one."""
        _, chart, dashboard = self.make_content(run_as_owner=1)
        self.share_dashboard_with(dashboard.name, OUTSIDER)

        for user, may_filter in ((OUTSIDER, False), (OWNER, True)):
            with as_user(user), db_connections():
                card = get_chart_data(chart=chart.name, dashboard=dashboard.name)
            self.assertIs(card["can_filter"], may_filter, user)

    # @feature dashboard.drill permissions.non-insights-user
    def test_a_reader_without_an_insights_role_breaks_down_no_chart_run_as_its_owner(self):
        """The dashboard's visibility admits them, but the owner saved only the
        chart. A breakdown is the owner's rows grouped another way."""
        _, chart, dashboard = self.make_content(run_as_owner=1)
        self.assertNotIn("Insights User", frappe.get_roles(DESK_USER))

        result = self.view_drill(
            DESK_USER, chart.name, dashboard.name, drill_stack=[breakdown_level("priority")]
        )

        self.assertEqual(result, {"columns": [], "rows": [], "not_permitted": {"doctypes": []}})

    # @feature charts.drill-rows permissions.non-insights-user
    def test_a_reader_admitted_by_the_level_alone_gets_no_rows_behind_the_picture(self):
        """`Everyone` shares the chart, not the rows it aggregates. Those rows are
        fetched under the owner's permissions and hold columns the card never
        showed. Paging through them reaches the same rows the file holds, so both
        ask the same question.

        The refusal is an answer, like every refusal on a dashboard the reader may
        open. The card's answer says the rows are not available, so the menu does
        not show View rows."""
        _, chart, dashboard = self.make_content()

        with as_user(DESK_USER), db_connections():
            self.assertFalse(get_chart_data(chart=chart.name, dashboard=dashboard.name)["drill"]["can_rows"])

        for endpoint, kwargs, refused in (
            (get_drill_data, {}, {"columns": [], "rows": [], "not_permitted": {"doctypes": []}}),
            (get_drill_rows_values, {"column": "description"}, []),
            (get_drill_rows_range, {"column": "description"}, None),
        ):
            with as_user(DESK_USER), db_connections():
                self.assertEqual(
                    endpoint(
                        chart=chart.name,
                        dashboard=dashboard.name,
                        drill_stack=[rows_level()],
                        **kwargs,
                    ),
                    refused,
                )

    # @feature dashboard.drill permissions.chart-run-as-owner
    def test_the_drill_runs_under_the_permissions_the_chart_declares(self):
        _, chart, dashboard = self.make_content(run_as_owner=0)

        result = self.view_drill(
            DESK_USER, chart.name, dashboard.name, drill_stack=[breakdown_level("priority")]
        )

        # with `run_as_owner` off, the engine applies the reader's own permissions,
        # so a reader with no role sees none of the owner's rows
        self.assertEqual(result["rows"], [])

    # @feature permissions.denied-is-not-found
    def test_an_outsider_is_answered_like_a_missing_reference(self):
        _, chart, dashboard = self.make_content(visibility="Private")

        with as_user(OUTSIDER):
            for reference, on_dashboard in ((chart.name, None), (chart.name, dashboard.name)):
                with self.assertRaises(frappe.DoesNotExistError):
                    get_drill_data(chart=reference, dashboard=on_dashboard, drill_stack=[rows_level()])

    # @feature shared.no-drill
    def test_a_guest_gets_no_drill_on_public_content(self):
        _, chart, dashboard = self.make_content()
        dashboard.db_set("visibility", "Public", update_modified=False)

        with as_user(GUEST), db_connections():
            # the chart is public, but it cannot be drilled
            response = get_chart_data(chart=chart.name, dashboard=dashboard.name, force=True)
            self.assertEqual(response["drill"]["dimensions"], [])

            with self.assertRaises(frappe.PermissionError) as raised:
                get_drill_data(chart=chart.name, dashboard=dashboard.name, drill_stack=[rows_level()])

        self.assertNotIsInstance(raised.exception, frappe.DoesNotExistError)

    # @feature charts.drill-rows-reading charts.drill-rows-filter permissions.chart-run-as-owner
    def test_a_readers_own_permissions_narrow_the_page_and_the_total_under_it(self):
        """The filters, the find and the count all run inside the permission the
        chart declares, so none of them can report rows the reader is not shown."""
        _, chart, dashboard = self.make_content(run_as_owner=0)
        # a rows level needs the reader's own grant. Their permissions still
        # decide which rows it returns
        self.share_dashboard_with(dashboard.name, DESK_USER)

        result = self.view_drill(
            DESK_USER,
            chart.name,
            dashboard.name,
            drill_stack=[rows_level()],
            find="open",
            row_filters=[rule("priority", "=", "High")],
        )

        self.assertEqual(self.descriptions(result), [])
        self.assertEqual(result["total_row_count"], 0)

    # what a reader may take away

    def view_export(self, user, chart, dashboard, **kwargs):
        with as_user(user), db_connections():
            return download_drill_rows(chart=chart, dashboard=dashboard, **kwargs)

    def exported(self, csv):
        return [line for line in csv.splitlines() if line.strip()]

    # @feature charts.drill-rows-export charts.drill-rows-filter
    def test_the_export_is_the_cut_the_reader_is_reading(self):
        _, chart, dashboard = self.make_content()

        csv = self.view_export(
            OWNER,
            chart.name,
            dashboard.name,
            drill_stack=[rows_level()],
            find="open",
            sort=[{"column": "description", "direction": "desc"}],
        )

        lines = self.exported(csv)
        self.assertIn("description", lines[0])
        self.assertEqual(len(lines), 3)
        self.assertIn(OPEN_LOW, lines[1])
        self.assertIn(OPEN_HIGH, lines[2])
        # the find narrows the file the way it narrows the page
        self.assertNotIn(CLOSED_HIGH, csv)

        filtered = self.view_export(
            OWNER,
            chart.name,
            dashboard.name,
            drill_stack=[rows_level()],
            row_filters=[rule("priority", "=", "Low")],
        )

        # and so do the reader's filters: the file holds only the rows the dialog
        # would show
        self.assertEqual(len(self.exported(filtered)), 2)
        self.assertIn(OPEN_LOW, filtered)

    # @feature charts.drill-rows-export permissions.non-insights-user
    def test_a_reader_admitted_by_the_level_alone_takes_no_file(self):
        """`Everyone` shares the chart, not the rows it aggregates. Those rows
        are fetched under the owner's permissions, and nobody granted them to
        this reader."""
        _, chart, dashboard = self.make_content()

        with self.assertRaises(frappe.PermissionError):
            self.view_export(DESK_USER, chart.name, dashboard.name, drill_stack=[rows_level()])

    # @feature charts.drill-rows-export permissions.non-insights-user permissions.download-gated
    def test_a_reader_takes_the_file_of_a_chart_run_as_them_whatever_roles_they_hold(self):
        """The export gate asks a role about `export` only when the reader holds
        an Insights role, and it asks only about `Insights Query v3`. So the
        `export` permission on a chart or dashboard does not decide it either.
        The reader's own permissions match none of the fixture rows, so the file
        is only its header."""
        _, chart, dashboard = self.make_content(run_as_owner=0)
        self.assertNotIn("Insights User", frappe.get_roles(DESK_USER))
        with as_user(DESK_USER):
            # neither doctype's `export` is granted to a role they hold
            self.assertFalse(frappe.has_permission(DT.CHART, ptype="export"))
            self.assertFalse(frappe.has_permission(DT.QUERY, ptype="export"))

        csv = self.view_export(DESK_USER, chart.name, dashboard.name, drill_stack=[rows_level()])

        self.assertEqual(len(self.exported(csv)), 1)

    # @feature charts.drill-rows charts.drill-rows-export permissions.visibility permissions.chart-run-as-owner
    def test_no_level_hands_out_the_owners_rows(self):
        """`standard_dashboard_visibility` sets every shipped dashboard to
        `Roles`. A visibility level lets a reader see the chart. The rows behind
        it come only from the chart running as the reader. `Roles` is narrower
        than `Everyone`, so it gives no more than `Everyone` does."""
        for level in ("Roles", "Everyone"):
            for box in (0, 1):
                with self.subTest(level=level, run_as_owner=box):
                    _, chart, dashboard = self.make_content(
                        visibility=level,
                        run_as_owner=box,
                        title=f"{DASHBOARD_TITLE} {level} {box}",
                    )
                    if level == "Roles":
                        board = frappe.get_doc(DT.DASHBOARD, dashboard.name)
                        board.append("visible_to_roles", {"role": "Insights User"})
                        board.save(ignore_permissions=True)
                    self.assertIn("Insights User", frappe.get_roles(OUTSIDER))

                    with as_user(OUTSIDER), db_connections():
                        card = get_chart_data(chart=chart.name, dashboard=dashboard.name)
                    answer = self.view_drill(OUTSIDER, chart.name, dashboard.name, drill_stack=[rows_level()])

                    if not box:
                        # the chart runs as its reader, so its rows are theirs
                        self.assertTrue(card["drill"]["can_rows"])
                        self.assertEqual(self.descriptions(answer), [OUTSIDER_TODO])
                        self.assertTrue(answer["can_export"])
                        continue

                    self.assertFalse(card["drill"]["can_rows"])
                    self.assertEqual(answer["rows"], [])
                    with self.assertRaises(frappe.PermissionError):
                        self.view_export(OUTSIDER, chart.name, dashboard.name, drill_stack=[rows_level()])

    # @feature charts.drill-rows-export permissions.download-gated
    def test_a_role_the_site_denied_the_export_takes_no_file_here_either(self):
        """The drill's file is the query's file in another form, so it asks the
        person the same question. Holding no Insights role is not the same as
        holding one the site removed `export` from."""
        from frappe.permissions import update_permission_property

        # a chart that runs as them, so the role is the only thing left to refuse
        _, chart, dashboard = self.make_content(run_as_owner=0)
        self.assertIn("Insights User", frappe.get_roles(OUTSIDER))

        update_permission_property(DT.QUERY, "Insights User", 0, "export", 0)
        frappe.clear_cache(doctype=DT.QUERY)
        self.addCleanup(frappe.clear_cache, doctype=DT.QUERY)
        self.addCleanup(update_permission_property, DT.QUERY, "Insights User", 0, "export", 1)

        answer = self.view_drill(OUTSIDER, chart.name, dashboard.name, drill_stack=[rows_level()])
        self.assertFalse(answer["can_export"])

        with self.assertRaises(frappe.PermissionError):
            self.view_export(OUTSIDER, chart.name, dashboard.name, drill_stack=[rows_level()])

    # @feature charts.drill-rows-export settings.allow-download
    def test_a_site_that_allows_no_download_offers_the_reader_none(self):
        """The setting is about data leaving the site as a file. It removes the
        file and keeps the page the reader is looking at."""
        # a chart that runs as them, so the toggle is the only thing left to refuse
        _, chart, dashboard = self.make_content(run_as_owner=0)
        frappe.db.set_single_value(DT.SETTINGS, "allow_download", 0)
        self.addCleanup(frappe.db.set_single_value, DT.SETTINGS, "allow_download", 1)

        answer = self.view_drill(OUTSIDER, chart.name, dashboard.name, drill_stack=[rows_level()])

        self.assertEqual(self.descriptions(answer), [OUTSIDER_TODO])
        self.assertFalse(answer["can_export"])
        with self.assertRaises(frappe.PermissionError):
            self.view_export(OUTSIDER, chart.name, dashboard.name, drill_stack=[rows_level()])

    # @feature charts.drill-rows-export
    def test_only_the_rows_behind_a_segment_can_be_taken_away(self):
        """A breakdown summarizes the segment. It is not the segment's rows."""
        _, chart, dashboard = self.make_content()

        answer = self.view_drill(OWNER, chart.name, dashboard.name, drill_stack=[breakdown_level("priority")])
        self.assertNotIn("can_export", answer)

        with self.assertRaises(frappe.ValidationError):
            self.view_export(OWNER, chart.name, dashboard.name, drill_stack=[breakdown_level("priority")])

    # @feature shared.no-drill
    def test_a_guest_cannot_take_the_rows_behind_a_public_chart_away(self):
        _, chart, dashboard = self.make_content()
        dashboard.db_set("visibility", "Public", update_modified=False)

        with as_user(GUEST), db_connections():
            with self.assertRaises(frappe.PermissionError) as raised:
                download_drill_rows(chart=chart.name, dashboard=dashboard.name, drill_stack=[rows_level()])

        self.assertNotIsInstance(raised.exception, frappe.DoesNotExistError)

    # @feature charts.drill-rows
    def test_a_stack_without_a_level_asks_for_nothing(self):
        _, chart, dashboard = self.make_content()

        with self.assertRaises(frappe.ValidationError):
            self.drill(OWNER, chart.name, dashboard.name, drill_stack=[])
