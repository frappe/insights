"""What a number a chart drew is made of, level by level.

The walk is `chart_drill`'s: a chart document, a stack of levels, and the rows
behind the segment the stack describes. It is tested at the layer, under the
author who built the chart, because the layer is what every endpoint shares.
`test_authoring_api` covers the builder's endpoint and what it adds.
"""

import json
from unittest.mock import patch

import frappe

from insights.insights.doctype.insights_chart_v3.chart_drill import drill_data, drill_dimensions
from insights.insights.doctype.insights_dashboard_v3.insights_dashboard_v3 import route_filters
from insights.insights.doctype.insights_data_source_v3.insights_data_source_v3 import db_connections
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import DT, as_user, create_user, delete_users, delete_workbooks

AUTHOR = "drill_api_author@test.com"

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
# those three by the number a ranked rows page puts first, biggest first
BY_WEIGHT = sorted(AUTHOR_TODOS, key=len, reverse=True)

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


def rows_level(filters=None, measure=None):
    return {"segment_filters": filters or [], "action": {"rows": True, "measure": measure}}


def breakdown_level(dimension_name, filters=None, measure=None, granularity=None):
    action = {"breakdown": dimension_name, "measure": measure}
    if granularity:
        action["granularity"] = granularity

    return {"segment_filters": filters or [], "action": action}


def equals(column, value):
    return {"column": column, "operator": "=", "value": value}


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
        cls.cleanup()

        create_user(AUTHOR, first_name="Drill", last_name="Author", roles="Insights User")

        for description, (status, priority) in AUTHOR_TODOS.items():
            cls.make_todo(description, status, priority, AUTHOR)
        for description, (date, priority) in TIMELINE_TODOS.items():
            cls.make_todo(description, "Open", priority, AUTHOR, date=date)

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

    @classmethod
    def cleanup(cls):
        delete_workbooks(title_prefix=WORKBOOK_TITLE)
        for prefix in (TODO_PREFIX, TIMELINE_PREFIX):
            for todo in frappe.get_all(
                "ToDo", filters={"description": ["like", f"%{prefix}%"]}, pluck="name"
            ):
                frappe.delete_doc("ToDo", todo, force=True, ignore_permissions=True)
        delete_users(AUTHOR)

    # fixtures

    def make_content(
        self,
        chart_type="Bar",
        config=None,
        title=DASHBOARD_TITLE,
        operations=None,
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
                }
            ).insert()
            dashboard = frappe.get_doc(
                {
                    "doctype": DT.DASHBOARD,
                    "title": title,
                    "workbook": workbook.name,
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

    def test_a_rows_level_returns_the_rows_behind_the_segment(self):
        _, chart, dashboard = self.make_content()

        result = self.drill(
            AUTHOR,
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

    def test_a_breakdown_level_groups_the_segment_by_the_chosen_dimension(self):
        _, chart, dashboard = self.make_content()

        result = self.drill(
            AUTHOR,
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
            AUTHOR,
            chart.name,
            dashboard.name,
            drill_stack=[breakdown_level("creation", measure="count_of_rows")],
        )

        # the fixtures are created within one second, so the span asks for the finest
        # grain the ladder offers and they all land within a bucket of it
        self.assertEqual(result["granularity"], "minute")
        self.assertEqual(sum(row["count_of_rows"] for row in result["rows"]), len(AUTHOR_TODOS))

    def test_a_breakdown_is_cut_to_a_ranking(self):
        """The level answers which slice explains the number, so it ranks a few.

        The cut is proven against a smaller bound than the shipped one: the
        fixtures hold three descriptions, and committing twenty-odd more would
        put them in front of every other test in this class.
        """
        _, chart, dashboard = self.make_content()

        with patch("insights.insights.doctype.insights_chart_v3.chart_drill.BREAKDOWN_SIZE", 2):
            result = self.drill(
                AUTHOR,
                chart.name,
                dashboard.name,
                drill_stack=[breakdown_level("description", measure="count_of_rows")],
            )

        self.assertEqual(len(result["rows"]), 2)
        # the dialog says "top 2 of 3", so the count has to see past the cut
        self.assertEqual(result["total_row_count"], 3)

    def test_a_rows_level_is_not_cut_to_a_ranking(self):
        """A rows page is bounded by the page size, not the ranking size."""
        _, chart, dashboard = self.make_content()

        with patch("insights.insights.doctype.insights_chart_v3.chart_drill.BREAKDOWN_SIZE", 1):
            result = self.drill(
                AUTHOR,
                chart.name,
                dashboard.name,
                drill_stack=[rows_level(measure="count_of_rows")],
            )

        self.assertEqual(len(result["rows"]), 3)

    # the order a rows page comes back in

    def test_a_rows_page_is_ranked_by_the_measure_that_was_clicked(self):
        """One page is shown, so it holds the rows that made the number biggest."""
        _, chart, dashboard = self.make_content(
            operations=weighted_operations(), config=bar_config([weight()])
        )

        result = self.drill(AUTHOR, chart.name, dashboard.name, drill_stack=[rows_level(measure="Weight")])

        self.assertEqual([row["description"] for row in result["rows"]], BY_WEIGHT)

    def test_a_rows_page_that_names_no_measure_follows_the_chart_s_own(self):
        _, chart, dashboard = self.make_content(
            operations=weighted_operations(), config=bar_config([weight()])
        )

        result = self.drill(AUTHOR, chart.name, dashboard.name, drill_stack=[rows_level()])

        self.assertEqual([row["description"] for row in result["rows"]], BY_WEIGHT)

    def test_a_measure_with_no_number_under_it_leaves_the_page_unranked(self):
        """Counting rows ranks none of them, and a name is no size."""
        _, chart, dashboard = self.make_content(config=bar_config([count()]))

        result = self.drill(AUTHOR, chart.name, dashboard.name, drill_stack=[rows_level(measure="Todos")])

        self.assertEqual(self.descriptions(result), sorted(AUTHOR_TODOS))

    # the order a breakdown comes back in
    #
    # One rule: a dimension with an order of its own is shown in that order, and
    # a dimension without one is ranked by the measure.

    def test_a_dimension_with_an_order_of_its_own_is_shown_in_it(self):
        _, chart, dashboard = self.timeline()

        result = self.drill(AUTHOR, chart.name, dashboard.name, drill_stack=[breakdown_level("date")])

        # a ranking would put February first and read as noise. A series reads
        # forwards, whatever the sizes along it
        self.assertEqual(self.buckets(result), TIMELINE_MONTHS)
        self.assertEqual([row["count_of_rows"] for row in result["rows"]], TIMELINE_COUNTS)

    def test_a_dimension_without_one_is_still_ranked_by_the_measure(self):
        _, chart, dashboard = self.timeline()

        result = self.drill(AUTHOR, chart.name, dashboard.name, drill_stack=[breakdown_level("priority")])

        # biggest first, which is the only reading a set of labels has
        self.assertEqual(
            [(row["priority"], row["count_of_rows"]) for row in result["rows"]],
            [("Low", 4), ("High", 2)],
        )

    def test_the_answer_says_which_way_its_rows_run_and_what_they_are_bucketed_by(self):
        _, chart, dashboard = self.timeline()

        ordered = self.drill(AUTHOR, chart.name, dashboard.name, drill_stack=[breakdown_level("date")])
        ranked = self.drill(AUTHOR, chart.name, dashboard.name, drill_stack=[breakdown_level("priority")])
        behind = self.drill(AUTHOR, chart.name, dashboard.name, drill_stack=[rows_level()])

        # the client draws by what it is told, never by a column type it guesses from
        self.assertEqual((ordered["ordered"], ordered["granularity"]), (True, "month"))
        self.assertEqual((ranked["ordered"], ranked["granularity"]), (False, None))
        self.assertEqual((behind["ordered"], behind["granularity"]), (False, None))

    def test_the_answer_says_whether_its_groups_add_up_to_the_segment_above_them(self):
        """A level read as parts of one whole rests on this, and the answer's own
        columns cannot supply it: nothing in a column of decimals says whether
        they hold sums or averages."""
        _, counted, dashboard = self.timeline()
        _, averaged, average_dashboard = self.timeline(config=bar_config(measures=[average()]))

        added = self.drill(AUTHOR, counted.name, dashboard.name, drill_stack=[breakdown_level("priority")])
        averages = self.drill(
            AUTHOR,
            averaged.name,
            average_dashboard.name,
            drill_stack=[breakdown_level("priority")],
        )
        behind = self.drill(AUTHOR, counted.name, dashboard.name, drill_stack=[rows_level()])

        self.assertTrue(added["additive"])
        # two groups' averages do not average, so these are not parts of anything
        self.assertFalse(averages["additive"])
        # a rows level groups nothing, so it has no groups to add
        self.assertFalse(behind["additive"])

    def test_the_grain_follows_the_span_of_the_segment_being_drilled(self):
        """A fixed default is arbitrary: one month of data is not ten years of it."""
        _, chart, dashboard = self.timeline()

        year = self.drill(AUTHOR, chart.name, dashboard.name, drill_stack=[breakdown_level("date")])
        february = self.drill(
            AUTHOR,
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

    def test_an_ordered_breakdown_is_cut_to_its_most_recent_stretch(self):
        """Never a top-N by measure, which would take buckets out of the middle."""
        _, chart, dashboard = self.timeline()

        with patch("insights.insights.doctype.insights_chart_v3.chart_drill.BREAKDOWN_SIZE", 2):
            result = self.drill(
                AUTHOR,
                chart.name,
                dashboard.name,
                drill_stack=[breakdown_level("date", granularity="month")],
            )

        # the two most recent months, still forwards. A ranking would have kept
        # February, the biggest, and left a hole where June was
        self.assertEqual(self.buckets(result), TIMELINE_MONTHS[-2:])
        self.assertEqual(result["total_row_count"], len(TIMELINE_MONTHS))

    def test_a_grain_the_caller_names_outranks_the_derived_one(self):
        _, chart, dashboard = self.timeline()

        result = self.drill(
            AUTHOR,
            chart.name,
            dashboard.name,
            drill_stack=[breakdown_level("date", granularity="year")],
        )

        # the reader changed the grain on the level, so the span has no say
        self.assertEqual(result["granularity"], "year")
        self.assertEqual(self.buckets(result), ["2024-01-01"])
        self.assertEqual(result["rows"][0]["count_of_rows"], len(TIMELINE_TODOS))

    def test_a_grain_the_column_cannot_admit_is_refused(self):
        timed = [
            *todo_operations(TIMELINE_PREFIX),
            {"type": "cast", "column": {"type": "column", "column_name": "creation"}, "data_type": "Time"},
        ]
        _, chart, dashboard = self.make_content()
        _, timed_chart, timed_dashboard = self.make_content(operations=timed)

        refused = (
            # a Time has no date part to take a month out of
            (timed_chart, timed_dashboard, breakdown_level("creation", granularity="month")),
            # and a label has no order at all, so no grain can bucket it
            (chart, dashboard, breakdown_level("priority", granularity="month")),
            (chart, dashboard, breakdown_level("creation", granularity="fortnight")),
        )
        for on_chart, on_dashboard, level in refused:
            with self.assertRaises(frappe.ValidationError) as raised:
                self.drill(AUTHOR, on_chart.name, on_dashboard.name, drill_stack=[level])
            self.assertIn("cannot be broken down by", str(raised.exception))

    def test_a_time_column_is_bucketed_by_a_grain_it_has(self):
        """Hour, minute and second are all a column with no date part admits."""
        timed = [
            *todo_operations(),
            {"type": "cast", "column": {"type": "column", "column_name": "creation"}, "data_type": "Time"},
        ]
        _, chart, dashboard = self.make_content(operations=timed)

        result = self.drill(AUTHOR, chart.name, dashboard.name, drill_stack=[breakdown_level("creation")])

        self.assertTrue(result["ordered"])
        # the fixtures are created within one second, so the ladder floors on its finest
        self.assertEqual(result["granularity"], "second")

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
            AUTHOR,
            chart.name,
            dashboard.name,
            drill_stack=[breakdown_level("priority", filters=[equals("status", "Open")], measure="Todos")],
        )

        self.assertEqual(self.column_names(result), ["priority", "Todos"])

    def test_segments_accumulate_down_the_stack(self):
        _, chart, dashboard = self.make_content()

        result = self.drill(
            AUTHOR,
            chart.name,
            dashboard.name,
            drill_stack=[
                breakdown_level("priority", filters=[equals("status", "Open")], measure="count_of_rows"),
                rows_level(filters=[equals("priority", "High")], measure="count_of_rows"),
            ],
        )

        # the status of the first level and the priority of the second, both
        self.assertEqual(self.descriptions(result), [OPEN_HIGH])

    def test_a_number_card_drills_on_an_empty_segment(self):
        _, chart, dashboard = self.make_content(
            chart_type="Number", config={"number_columns": [count("Todos")]}
        )

        result = self.drill(AUTHOR, chart.name, dashboard.name, drill_stack=[rows_level(measure="Todos")])

        self.assertEqual(self.descriptions(result), sorted(AUTHOR_TODOS))

    def test_a_windowed_card_drills_into_the_window_it_reads(self):
        """A card holding one window against another draws only the first.

        The pipeline under it carries both, as the Or of every window the card
        fetches, so a click that pinned nothing came back with both months.
        """
        _, chart, dashboard = self.timeline(
            chart_type="Number",
            config={
                "number_columns": [count("Todos")],
                "date_column": dimension("date", "Date"),
                # anchored, so the window the card reads is the fixtures' February
                "window": {"span": "current month", "anchor": "2024-02-15"},
                "number_column_options": [{"comparison": {"source": "previous"}}],
            },
        )

        result = self.drill(
            AUTHOR,
            chart.name,
            dashboard.name,
            drill_stack=[rows_level(filters=[equals("date", TIMELINE_MONTHS[1])], measure="Todos")],
        )

        # February alone: January is in the pipeline only because the card
        # compares against it
        self.assertEqual(self.descriptions(result), FEBRUARY)

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
            AUTHOR,
            chart.name,
            dashboard.name,
            # the newest bucket, which is the one the card reads
            drill_stack=[rows_level(filters=[equals("date", TIMELINE_MONTHS[-1])], measure="Todos")],
        )

        self.assertEqual(self.descriptions(result), [f"{TIMELINE_PREFIX} december"])

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

        result = self.drill(AUTHOR, chart.name, dashboard.name, drill_stack=[rows_level(measure="Open")])

        # the rows behind the number are the ones the measure counted
        self.assertEqual(self.descriptions(result), sorted([OPEN_HIGH, OPEN_LOW]))

    # a segment the chart spread across its columns

    def test_a_pivot_cell_pins_the_row_and_the_column(self):
        _, chart, dashboard = self.make_content(chart_type="Table", config=pivot_config())

        result = self.drill(
            AUTHOR,
            chart.name,
            dashboard.name,
            # the cell under the "High" column, on the "Open" row: the row
            # dimension and the column dimension pin together
            drill_stack=[
                rows_level(filters=[equals("status", "Open"), equals("priority", "High")], measure="Todos")
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
            AUTHOR,
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
            AUTHOR,
            chart.name,
            dashboard.name,
            drill_stack=[rows_level(filters=[equals("creation", str(this_month))])],
        )
        empty = self.drill(
            AUTHOR,
            chart.name,
            dashboard.name,
            drill_stack=[
                rows_level(filters=[equals("creation", str(frappe.utils.add_months(this_month, -1)))])
            ],
        )

        self.assertEqual(self.descriptions(rows), sorted(AUTHOR_TODOS))
        self.assertEqual(empty["rows"], [])

    # a bucket a level of the stack made for itself
    #
    # The chart's own step is not the only thing that buckets a date: a
    # breakdown level groups one at a grain of its own, and a click on one of
    # those bars pins a bucket no step of the chart has ever heard of.

    def test_a_bucket_a_level_made_is_drilled_as_the_span_it_covers(self):
        _, chart, dashboard = self.timeline()

        result = self.drill(
            AUTHOR,
            chart.name,
            dashboard.name,
            drill_stack=[
                breakdown_level("date", granularity="month"),
                rows_level(filters=[equals("date", TIMELINE_MONTHS[1])]),
            ],
        )

        # the whole month, not the instant its first bucket starts at
        self.assertEqual(self.descriptions(result), FEBRUARY)

    def test_a_bucket_a_level_made_narrows_the_level_below_it(self):
        _, chart, dashboard = self.timeline()

        result = self.drill(
            AUTHOR,
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

    def test_a_bucket_made_under_a_categorical_level_is_still_a_span(self):
        _, chart, dashboard = self.timeline()

        result = self.drill(
            AUTHOR,
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

    def test_a_level_that_names_no_grain_pins_the_value_it_was_given(self):
        """A caller with no answer to echo yet, or one that never echoes."""
        _, chart, dashboard = self.timeline()

        result = self.drill(
            AUTHOR,
            chart.name,
            dashboard.name,
            drill_stack=[
                breakdown_level("date"),
                rows_level(filters=[equals("date", "2024-02-15")]),
            ],
        )

        self.assertEqual(self.descriptions(result), [f"{TIMELINE_PREFIX} february one"])

    def test_a_grain_an_earlier_level_cannot_admit_is_refused(self):
        _, chart, dashboard = self.timeline()

        with self.assertRaises(frappe.ValidationError) as raised:
            self.drill(
                AUTHOR,
                chart.name,
                dashboard.name,
                drill_stack=[
                    breakdown_level("date", granularity="fortnight"),
                    rows_level(filters=[equals("date", TIMELINE_MONTHS[1])]),
                ],
            )

        self.assertIn("cannot be broken down by", str(raised.exception))

    # the wire cannot widen what the chart exposes

    def test_a_column_that_is_not_on_the_surface_is_refused(self):
        _, chart, dashboard = self.make_content()

        for stack in (
            [rows_level(filters=[equals("tabUser.password", "x")])],
            [breakdown_level("password")],
        ):
            with self.assertRaises(frappe.ValidationError) as raised:
                self.drill(AUTHOR, chart.name, dashboard.name, drill_stack=stack)
            self.assertIn("is not a column", str(raised.exception))

    def test_no_drill_response_carries_the_query_behind_the_chart(self):
        query, chart, dashboard = self.make_content()

        result = self.drill(
            AUTHOR,
            chart.name,
            dashboard.name,
            drill_stack=[rows_level(filters=[equals("status", "Open")])],
        )

        serialized = json.dumps(result, default=str)
        for leak in ("operations", "raw_sql", "tabToDo", query.name):
            self.assertNotIn(leak, serialized, f"{leak} must not reach a reader")
        self.assertNotIn("sql", result)

    # what the menu offers before anything is clicked

    def test_the_chart_offers_the_dimensions_of_the_pre_summarize_surface(self):
        _, chart, _ = self.make_content()

        with as_user(AUTHOR), db_connections():
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

    # the record behind a row

    def test_a_drilled_row_names_the_desk_record_it_opens(self):
        _, chart, dashboard = self.make_content()

        result = self.drill(
            AUTHOR,
            chart.name,
            dashboard.name,
            drill_stack=[rows_level(filters=[equals("status", "Open")])],
        )

        # the row's own document, and the Link fields beside it on the same row
        self.assertEqual(result["record_links"]["name"], "ToDo")
        self.assertEqual(result["record_links"]["allocated_to"], "User")

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
            AUTHOR,
            chart.name,
            dashboard.name,
            drill_stack=[rows_level(filters=[equals("status", "Open")])],
        )

        # a rename says what the column is called, not what it holds, so the link
        # follows it rather than giving up on it
        self.assertEqual(result["record_links"]["todo_id"], "ToDo")
        self.assertNotIn("name", result["record_links"])

    def test_a_dropped_name_column_carries_no_record_link(self):
        dropped = [
            *todo_operations(),
            {"type": "select", "column_names": ["status", "priority"]},
        ]
        _, chart, dashboard = self.make_content(operations=dropped)

        result = self.drill(
            AUTHOR,
            chart.name,
            dashboard.name,
            drill_stack=[rows_level(filters=[equals("status", "Open")])],
        )

        # nothing on the row names a document, so the client is told nothing
        # rather than told a record that might be the wrong one
        self.assertNotIn("record_links", result)

    def test_a_child_row_does_not_name_itself(self):
        _, chart, dashboard = self.make_content(
            operations=has_role_operations(),
            config=bar_config_over("parenttype"),
        )

        result = self.drill(
            AUTHOR,
            chart.name,
            dashboard.name,
            drill_stack=[rows_level(filters=[equals("parenttype", "User")])],
        )

        # a child row has no form of its own — the desk routes the parent, which
        # the row cannot name. The Link fields beside it still name theirs
        self.assertNotIn("name", result["record_links"])
        self.assertEqual(result["record_links"]["role"], "Role")

    def test_only_a_rows_level_carries_record_links(self):
        _, chart, dashboard = self.make_content()

        result = self.drill(
            AUTHOR,
            chart.name,
            dashboard.name,
            drill_stack=[breakdown_level("priority", filters=[equals("status", "Open")])],
        )

        self.assertNotIn("record_links", result)

    # dashboard filters

    def test_dashboard_filter_state_reaches_the_drill(self):
        _, chart, dashboard = self.make_content()

        result = self.drill(
            AUTHOR,
            chart.name,
            dashboard.name,
            filters={"Description": {"operator": "contains", "value": "open low"}},
            drill_stack=[rows_level(filters=[equals("status", "Open")])],
        )

        # the rows agree with the number the filtered card was showing
        self.assertEqual(self.descriptions(result), [OPEN_LOW])

    def test_a_chart_keyed_filter_group_does_not_reach_the_drill(self):
        """A card filter lands after the chart's summarize, where the drill does not go."""
        query, chart, _ = self.make_content()

        adhoc_filters = {
            # a rule on the card's own measure. The drill's pipeline is sliced
            # before the summarize, so applying it there would throw
            chart.name: filter_group("count_of_rows", ">", 5),
            query.name: filter_group("description", "contains", "open low"),
        }

        with as_user(AUTHOR), db_connections():
            result = drill_data(
                chart,
                [rows_level(filters=[equals("status", "Open")])],
                adhoc_filters=adhoc_filters,
            )

        # the query-keyed group still narrows the rows
        self.assertEqual(self.descriptions(result), [OPEN_LOW])

    def test_a_stack_without_a_level_asks_for_nothing(self):
        _, chart, dashboard = self.make_content()

        with self.assertRaises(frappe.ValidationError):
            self.drill(AUTHOR, chart.name, dashboard.name, drill_stack=[])
