"""A chart the reader may view but whose data they may not read.

It does not run, and its card stays in place naming the doctypes it needs.
Never an empty result that stands for a missing permission — "No data" reads as
zero. See `docs/adr/a-reader-never-sees-a-false-empty.md`.
"""

import frappe

from insights.api.view import get_chart_data, get_dashboard
from insights.api.workbooks import update_share_permissions
from insights.insights.doctype.insights_data_source_v3.insights_data_source_v3 import db_connections
from insights.insights.doctype.insights_table_v3.insights_table_v3 import InsightsTablev3
from insights.not_permitted import NotPermitted
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import DT, as_user, create_user, delete_users, delete_workbooks

SITE_DB = "Site DB"
PREFIX = "Not Permitted Test"
WORKBOOK_TITLE = f"{PREFIX} Workbook"
READER = "not-permitted-reader@test.com"

# what an Insights User cannot read on a stock site: the doctype itself, and a
# child table whose only parent they cannot read either
UNREADABLE_TABLE = "tabError Log"
UNREADABLE_CHILD_TABLE = "tabWorkflow Document State"

# a dashboard filter that lands on the card nobody here may read
REFUSED_FILTER = "Refused"


def source(table_name):
    return [
        {
            "type": "source",
            "table": {"type": "table", "data_source": SITE_DB, "table_name": table_name},
        }
    ]


def join(table_name, columns, on="name"):
    return {
        "type": "join",
        "join_type": "left",
        "table": {"type": "table", "data_source": SITE_DB, "table_name": table_name},
        "join_condition": {
            "left_column": {"type": "column", "column_name": on},
            "right_column": {"type": "column", "column_name": "name"},
        },
        "select_columns": [{"type": "column", "column_name": column} for column in columns],
    }


class ContentOverATableTheReaderCannotRead(InsightsIntegrationTestCase):
    """One workbook: a chart over a table this reader cannot read, two over one
    they can, and a dashboard of each shape."""

    @classmethod
    def before_class(cls):
        cls.cleanup()
        create_user(READER, first_name="Not", last_name="Permitted", roles="Insights User")

        cls.todo = (
            frappe.get_doc(
                {
                    "doctype": "ToDo",
                    "description": f"{PREFIX} todo",
                    "status": "Open",
                    "allocated_to": READER,
                    "assigned_by": "Administrator",
                }
            )
            .insert(ignore_permissions=True)
            .name
        )

        workbook = frappe.get_doc({"doctype": DT.WORKBOOK, "title": WORKBOOK_TITLE}).insert()
        cls.workbook = workbook.name
        cls.unreadable_chart = cls.create_chart("Error Logs", source(UNREADABLE_TABLE), "name")
        cls.unreadable_query = frappe.db.get_value(DT.CHART, cls.unreadable_chart, "query")
        cls.permlevel_chart = cls.create_chart("Todo Statuses", source("tabToDo"), "status")
        cls.plain_chart = cls.create_chart("Todo Names", source("tabToDo"), "name")
        cls.refused_board = cls.create_dashboard("Refused", [cls.unreadable_chart])
        cls.partly_board = cls.create_dashboard(
            "Partly",
            [cls.unreadable_chart, cls.plain_chart],
            # a filter landing on the card nobody here may read
            links={cls.unreadable_chart: f"`{cls.unreadable_query}`.`name`"},
        )
        update_share_permissions(workbook.name, [{"user": READER, "read": 1, "write": 0}])

    @classmethod
    def after_class(cls):
        cls.cleanup()

    @classmethod
    def cleanup(cls):
        delete_workbooks(title_prefix=WORKBOOK_TITLE)
        for name in frappe.get_all("ToDo", filters={"description": ["like", f"%{PREFIX}%"]}, pluck="name"):
            frappe.delete_doc("ToDo", name, force=True, ignore_permissions=True)
        delete_users(READER)

    @classmethod
    def create_chart(cls, title, operations, column):
        query = frappe.get_doc(
            {
                "doctype": DT.QUERY,
                "title": f"{PREFIX} {title}",
                "workbook": cls.workbook,
                "use_live_connection": 1,
                "is_builder_query": 1,
                "operations": operations,
            }
        ).insert()
        return (
            frappe.get_doc(
                {
                    "doctype": DT.CHART,
                    "title": f"{PREFIX} {title}",
                    "workbook": cls.workbook,
                    "query": query.name,
                    "chart_type": "Table",
                    "config": {
                        "rows": [{"column_name": column, "dimension_name": column, "data_type": "String"}],
                        "columns": [],
                        "values": [],
                        "order_by": [],
                    },
                }
            )
            .insert()
            .name
        )

    @classmethod
    def create_dashboard(cls, title, charts, links=None):
        items = [{"id": str(i), "type": "chart", "chart": chart} for i, chart in enumerate(charts)]
        if links:
            items.append(
                {
                    "id": "filter",
                    "type": "filter",
                    "filter_name": REFUSED_FILTER,
                    "filter_type": "String",
                    "links": links,
                }
            )
        return (
            frappe.get_doc(
                {
                    "doctype": DT.DASHBOARD,
                    "title": f"{PREFIX} {title}",
                    "workbook": cls.workbook,
                    "items": items,
                }
            )
            .insert()
            .name
        )

    def read_table(self, table_name):
        with as_user(READER), db_connections():
            return InsightsTablev3.get_ibis_table(SITE_DB, table_name, use_live_connection=True)

    def fetch(self, chart):
        """The engine's own answer, which is a refusal. The wire surface above it
        turns that into something a card draws — see the boundary tests."""
        with as_user(READER), db_connections():
            return frappe.get_doc(DT.CHART, chart).fetch(force=True)


class ANotPermittedChartDoesNotRun(ContentOverATableTheReaderCannotRead):
    # @feature permissions.not-permitted-chart
    def test_a_table_the_reader_cannot_read_names_the_doctype_it_needs(self):
        with self.assertRaises(NotPermitted) as refusal:
            self.read_table(UNREADABLE_TABLE)

        self.assertEqual(refusal.exception.doctypes, ["Error Log"])

    # @feature permissions.not-permitted-chart
    def test_a_child_table_names_the_parent_it_needs(self):
        with self.assertRaises(NotPermitted) as refusal:
            self.read_table(UNREADABLE_CHILD_TABLE)

        self.assertEqual(refusal.exception.doctypes, ["Workflow"])

    # @feature permissions.not-permitted-chart
    def test_a_permlevel_column_refuses_only_the_chart_that_names_it(self):
        self.make_status_permlevel()

        with self.assertRaises(NotPermitted) as refusal:
            self.fetch(self.permlevel_chart)
        self.assertEqual(refusal.exception.doctypes, ["ToDo"])

        # the same table, read by a chart that never names the column
        rows = self.fetch(self.plain_chart)["rows"]
        self.assertEqual([row["name"] for row in rows], [self.todo])

    # @feature permissions.not-permitted-chart
    def test_a_join_that_names_a_permlevel_column_is_not_permitted(self):
        """Every other operation that names a column goes through `get_column`,
        which turns a held-back column into a refusal. A join's own selection
        used to go straight at ibis and come back as "check the Join
        operation" - an author error the reader can only retry."""
        self.make_status_permlevel()
        joined = self.create_chart("Joined Status", [*source("tabToDo"), join("tabToDo", ["status"])], "name")

        with self.assertRaises(NotPermitted) as refusal:
            self.fetch(joined)

        self.assertEqual(refusal.exception.doctypes, ["ToDo"])

    # @feature permissions.not-permitted-chart
    def test_a_joins_column_names_do_not_move_with_the_reader(self):
        """The permlevel projection runs before the join names its output, so a
        column held back from one reader would stop being a duplicate and the
        right-hand column would take the bare name the chart's operations mean
        for the left-hand one - a different column, with no refusal.

        The right side carries `status` past the projection because a mutate
        makes it, so only the left side loses it.
        """
        joined = frappe.get_doc(
            {
                "doctype": DT.QUERY,
                "title": f"{PREFIX} Joined Names",
                "workbook": self.workbook,
                "use_live_connection": 1,
                "is_builder_query": 1,
                "operations": self.mutated_status_join(),
            }
        ).insert()

        def column_names():
            with db_connections():
                result = frappe.get_doc(DT.QUERY, joined.name).execute(force=True)
            return [column["name"] for column in result["columns"]]

        as_author = column_names()
        # the right-hand `status` took the prefix, because the left had one too
        joined_column = next(name for name in as_author if name.endswith("_status"))

        self.make_status_permlevel()
        as_reader = column_names()

        self.assertIn(joined_column, as_reader)
        # and never the bare name, which the chart's operations mean for the left
        self.assertNotIn("status", as_reader)

    # @feature permissions.not-permitted-chart
    def test_the_held_back_column_is_refused_and_not_read_off_the_other_side(self):
        """The join renames the right-hand column so its name does not move with
        the reader, and then the only column ending in `_status` is that one. An
        operation naming the bare `status` means the left-hand column held back
        from this reader, so it is Not Permitted - the suffix and prefix
        recoveries are for a column stored under an older naming, which this is
        not."""
        joined = self.mutated_status_join()
        chart = self.create_chart("Joined Status Rows", joined, "status")

        self.assertTrue(self.fetch(chart)["rows"])

        self.make_status_permlevel()

        with self.assertRaises(NotPermitted) as refusal:
            self.fetch(chart)

        self.assertEqual(refusal.exception.doctypes, ["ToDo"])

    # @feature permissions.not-permitted-chart
    def test_an_operation_that_can_do_without_a_column_does_not_take_the_other_sides(self):
        """`throw` chooses what happens when a name resolves to nothing, not
        whether a held-back name may resolve to something else. A remove,
        a sort and a carried currency all name a column and carry on without
        it, and all three used to walk into the suffix recovery — which, after
        the join renamed the right-hand column, matches exactly it."""
        removed = [
            *self.mutated_status_join(),
            {"type": "remove", "column_names": ["status"]},
        ]
        query = frappe.get_doc(
            {
                "doctype": DT.QUERY,
                "title": f"{PREFIX} Removed Status",
                "workbook": self.workbook,
                "use_live_connection": 1,
                "is_builder_query": 1,
                "operations": removed,
            }
        ).insert()

        def column_names():
            with db_connections():
                result = frappe.get_doc(DT.QUERY, query.name).execute(force=True)
            return [column["name"] for column in result["columns"]]

        as_author = column_names()
        # the author's remove took the left-hand column, so the renamed
        # right-hand one is what is left
        joined_column = next(name for name in as_author if name.endswith("_status"))

        self.make_status_permlevel()

        # the left-hand column was held back before the remove named it, so
        # the remove has nothing to do - and the right-hand column is not it
        self.assertIn(joined_column, column_names())

    # @feature permissions.not-permitted-chart
    def test_a_column_dropped_before_the_join_is_not_put_back_at_it(self):
        """A held-back name is put back so the join names its output the way the
        author's does. Which is a question about the relation, not about every
        table under it: a summarise above the table drops the column for the
        author too, so the name means the other side's for both of them."""
        summarized = [
            *source("tabToDo"),
            {
                "type": "summarize",
                "measures": [
                    {
                        "measure_name": "todos",
                        "column_name": "name",
                        "data_type": "Integer",
                        "aggregation": "count",
                    }
                ],
                "dimensions": [{"dimension_name": "name", "column_name": "name", "data_type": "String"}],
            },
            {
                "type": "join",
                "join_type": "left",
                "table": {"type": "query", "query_name": self.mutated_status_query()},
                "join_condition": {
                    "left_column": {"type": "column", "column_name": "name"},
                    "right_column": {"type": "column", "column_name": "name"},
                },
                "select_columns": [{"type": "column", "column_name": "status"}],
            },
        ]
        chart = self.create_chart("Summarized Then Joined", summarized, "status")

        as_author = self.fetch(chart)
        self.assertIn("status", [column["name"] for column in as_author["columns"]])

        self.make_status_permlevel()

        # the same column, drawn the same way: the summarise left no `status` on
        # this side for either of them
        as_reader = self.fetch(chart)
        self.assertEqual(
            [column["name"] for column in as_reader["columns"]],
            [column["name"] for column in as_author["columns"]],
        )
        self.assertEqual(len(as_reader["rows"]), len(as_author["rows"]))

    # @feature permissions.not-permitted-chart
    def test_a_column_the_author_removed_or_renamed_does_not_hide_a_held_back_one(self):
        """A remove or a rename drops a name for the author as well, but only its
        own - the table's other columns still stand, so the held-back one
        is still the left-hand `status` and the join still has to prefix the
        right-hand one. `InsightsChartv3.fetch` builds the stored operations."""
        dropped_by_author = {
            "remove": {"type": "remove", "column_names": ["description"]},
            "rename": {
                "type": "rename",
                "column": {"type": "column", "column_name": "description"},
                "new_name": "details",
            },
        }
        charts = {}
        for kind, operation in dropped_by_author.items():
            [source_operation, joined] = self.mutated_status_join()
            charts[kind] = self.create_chart(
                f"{kind} Then Joined", [source_operation, operation, joined], "status"
            )
            # without a join the held-back column is refused, not an author's unknown column
            charts[f"{kind} alone"] = self.create_chart(kind, [source_operation, operation], "status")
            self.assertEqual(self.fetch(charts[kind])["rows"][0]["status"], "Open")

        self.make_status_permlevel()

        for kind, chart in charts.items():
            with self.subTest(kind):
                with self.assertRaises(NotPermitted) as refusal:
                    self.fetch(chart)
                self.assertEqual(refusal.exception.doctypes, ["ToDo"])

    # @feature permissions.not-permitted-chart
    def test_a_column_the_author_removed_and_the_build_held_back_is_not_refused(self):
        """`InsightsChartv3.fetch` builds the stored operations. The author took
        `status` off the left side, so the join's `status` is the right-hand
        one for both of them - holding back the left-hand one first does not
        make it theirs to be refused."""
        [source_operation, joined] = self.mutated_status_join()
        chart = self.create_chart(
            "Removed Then Joined",
            [source_operation, {"type": "remove", "column_names": ["status"]}, joined],
            "status",
        )
        as_author = self.fetch(chart)

        self.make_status_permlevel()

        as_reader = self.fetch(chart)
        self.assertEqual(
            [column["name"] for column in as_reader["columns"]],
            [column["name"] for column in as_author["columns"]],
        )
        self.assertEqual(as_reader["rows"], as_author["rows"])

    # @feature permissions.not-permitted-chart
    def test_a_remove_on_the_other_side_of_a_join_does_not_hand_it_the_held_back_name(self):
        """`InsightsChartv3.fetch` builds the stored operations. The right-hand
        query took its own `status` off and made a new one, so the left-hand
        `status` is still the chart's for the author - a reader it is held back
        from is refused, not drawn the right-hand column under its name. The right side
        is one hop away or two."""
        removed_then_made = [
            {"type": "remove", "column_names": ["status"]},
            {
                "type": "mutate",
                "new_name": "status",
                "data_type": "String",
                "expression": {"type": "expression", "expression": "priority"},
            },
        ]
        one_hop = self.create_query("Removed Then Made", [*source("tabToDo"), *removed_then_made])
        removed = self.create_query(
            "Removed", [*source("tabToDo"), {"type": "remove", "column_names": ["status"]}]
        )
        two_hops = self.create_query(
            "Sourced Then Made",
            [{"type": "source", "table": {"type": "query", "query_name": removed}}, removed_then_made[1]],
        )

        charts = {}
        for hops, right in {"one hop": one_hop, "two hops": two_hops}.items():
            [source_operation, joined] = self.mutated_status_join()
            joined["table"]["query_name"] = right
            charts[hops] = self.create_chart(f"Right {hops}", [source_operation, joined], "status")
            self.assertEqual(self.fetch(charts[hops])["rows"][0]["status"], "Open")

        self.make_status_permlevel()

        for hops, chart in charts.items():
            with self.subTest(hops):
                with self.assertRaises(NotPermitted) as refusal:
                    self.fetch(chart)
                self.assertEqual(refusal.exception.doctypes, ["ToDo"])

    # @feature permissions.not-permitted-chart
    def test_a_remove_the_left_side_did_not_make_does_not_hand_it_the_held_back_name(self):
        """`InsightsChartv3.fetch` builds the stored operations. A remove under
        an earlier join's right side, or one on the right that builds the same
        relation as the left's own for this reader, took nothing off the left:
        its `status` is still the chart's."""
        self.read_every_row()

        charts = {
            kind: self.create_chart(kind, operations, "status")
            for kind, operations in self.shapes_with_a_remove_off_the_left().items()
        }
        for chart in charts.values():
            self.assertIn("Open", [row["status"] for row in self.fetch(chart)["rows"]])

        self.make_status_permlevel()

        for kind, chart in charts.items():
            with self.subTest(kind):
                with self.assertRaises(NotPermitted) as refusal:
                    self.fetch(chart)
                self.assertEqual(refusal.exception.doctypes, ["ToDo"])

    # @feature permissions.not-permitted-chart
    def test_a_table_narrowed_by_rows_and_read_twice_draws_the_readers_rows(self):
        """`InsightsChartv3.fetch` builds the stored operations. For a reader
        narrowed by rows, a chart that reads `tabToDo` again through a second
        join, or through a union and a join, draws the reader's rows whether or
        not `status` is held back."""
        removed = self.create_query(
            "Removed", [*source("tabToDo"), {"type": "remove", "column_names": ["status"]}]
        )
        [source_operation, joined] = self.mutated_status_join()
        union = {"type": "union", "table": {"type": "query", "query_name": removed}, "distinct": True}
        charts = {
            "second join": self.create_chart(
                "second join names", self.shapes_with_a_remove_off_the_left()["second join"], "name"
            ),
            "union then joined": self.create_chart(
                "union then joined names", [source_operation, union, joined], "name"
            ),
        }

        for held_back in (False, True):
            if held_back:
                self.make_status_permlevel()
            for kind, chart in charts.items():
                with self.subTest(kind, held_back=held_back):
                    self.assertEqual([row["name"] for row in self.fetch(chart)["rows"]], [self.todo])

    # @feature permissions.not-permitted-chart
    def test_an_expression_that_names_a_held_back_column_is_not_permitted(self):
        """`InsightsChartv3.fetch` builds a mutate, an expression filter and an
        expression measure, and `InsightsAlert` evaluates its condition through
        `evaluate_alert_expression`. A held-back name is refused as a
        column operation's is, not a Python error the card offers to retry."""
        count_open = {
            "type": "summarize",
            "measures": [
                {
                    "data_type": "Integer",
                    "expression": {"type": "expression", "expression": "count_if(status == 'Open')"},
                    "measure_name": "open",
                }
            ],
            "dimensions": [{"dimension_name": "name", "column_name": "name", "data_type": "String"}],
        }
        charts = {
            "mutate": [*source("tabToDo"), self.mutate("state", "status")],
            "filter": [
                *source("tabToDo"),
                {"type": "filter", "expression": {"type": "expression", "expression": "status == 'Open'"}},
            ],
            "measure": [*source("tabToDo"), count_open],
        }
        charts = {kind: self.create_chart(kind, operations, "name") for kind, operations in charts.items()}
        # a column the reader still has, and a name no table held back
        kept = self.create_chart("kept", [*source("tabToDo"), self.mutate("state", "priority")], "name")
        unknown = self.create_chart(
            "unknown", [*source("tabToDo"), self.mutate("state", "no_such_column")], "name"
        )
        alerted = self.create_query("Alerted", source("tabToDo"))

        self.make_status_permlevel()

        for kind, chart in charts.items():
            with self.subTest(kind):
                with self.assertRaises(NotPermitted) as refusal:
                    self.fetch(chart)
                self.assertEqual(refusal.exception.doctypes, ["ToDo"])

        with as_user(READER), db_connections(), self.assertRaises(NotPermitted):
            frappe.get_doc(DT.QUERY, alerted).evaluate_alert_expression("status == 'Open'")

        self.assertEqual([row["name"] for row in self.fetch(kept)["rows"]], [self.todo])
        with self.assertRaises(NameError):
            self.fetch(unknown)

    def mutate(self, new_name, expression):
        return {
            "type": "mutate",
            "new_name": new_name,
            "data_type": "String",
            "expression": {"type": "expression", "expression": expression},
        }

    def read_every_row(self):
        """Let the reader past ToDo's row filter, so a wrong column has rows to
        draw and the chart reads the table without a row filter."""
        frappe.get_doc("User", READER).add_roles("System Manager")
        self.addCleanup(lambda: frappe.get_doc("User", READER).remove_roles("System Manager"))

    def shapes_with_a_remove_off_the_left(self):
        """Two charts whose left-hand `status` no remove of theirs took off."""
        removed = self.create_query(
            "Removed", [*source("tabToDo"), {"type": "remove", "column_names": ["status"]}]
        )
        removed_then_made = self.create_query(
            "Removed Two Then Made",
            [
                *source("tabToDo"),
                {"type": "remove", "column_names": ["description", "status"]},
                {
                    "type": "mutate",
                    "new_name": "status",
                    "data_type": "String",
                    "expression": {"type": "expression", "expression": "priority"},
                },
            ],
        )

        [source_operation, second_join] = self.mutated_status_join()
        first_join = {
            **second_join,
            "table": {"type": "query", "query_name": removed},
            "select_columns": [{"type": "column", "column_name": "description"}],
        }
        equal_remove = {**second_join, "table": {"type": "query", "query_name": removed_then_made}}
        return {
            "second join": [source_operation, first_join, second_join],
            "equal remove": [
                source_operation,
                {"type": "remove", "column_names": ["description"]},
                equal_remove,
            ],
        }

    # @feature permissions.not-permitted-chart
    def test_a_held_back_column_named_off_a_table_in_an_expression_is_not_permitted(self):
        """`InsightsChartv3.fetch` builds a join expression and a custom
        operation. `t1.status`, `t2.status` and `q.status` name the held-back
        column as a bare `status` does, and are refused as it is."""
        plain = self.create_query("Plain", source("tabToDo"))

        def joined(expression, columns=("priority",)):
            return [
                *source("tabToDo"),
                {
                    "type": "join",
                    "join_type": "left",
                    "table": {"type": "query", "query_name": plain},
                    "join_condition": {"join_expression": {"type": "expression", "expression": expression}},
                    "select_columns": [{"type": "column", "column_name": column} for column in columns],
                },
            ]

        def custom(expression):
            return [
                *source("tabToDo"),
                {"type": "custom_operation", "expression": {"type": "expression", "expression": expression}},
            ]

        on = "(t1.name == t2.name) & ({} == 'Open')"
        shapes = {
            "t1": joined(on.format("t1.status")),
            "t2": joined(on.format("t2.status")),
            "t1, nothing selected": joined(on.format("t1.status"), columns=()),
            "q": custom("q.filter(q.status == 'Open')"),
        }
        charts = {kind: self.create_chart(kind, operations, "name") for kind, operations in shapes.items()}
        # a column the reader still has, and a name no table held back
        kept = self.create_chart(
            "kept", joined(on.format("t2.priority").replace("'Open'", "t1.priority")), "name"
        )
        unknown = self.create_chart("unknown", custom("q.filter(q.no_such_column == 'Open')"), "name")

        self.make_status_permlevel()

        for kind, chart in charts.items():
            with self.subTest(kind):
                with self.assertRaises(NotPermitted) as refusal:
                    self.fetch(chart)
                self.assertEqual(refusal.exception.doctypes, ["ToDo"])

        self.assertEqual([row["name"] for row in self.fetch(kept)["rows"]], [self.todo])
        with self.assertRaises(AttributeError):
            self.fetch(unknown)

    # @feature permissions.not-permitted-chart
    def test_a_sql_column_that_names_a_held_back_column_is_not_permitted(self):
        """`InsightsChartv3.fetch` builds a migrated `sql_column`. Raw SQL
        naming a held-back column is refused as an expression naming it
        is, not a database error the card offers to retry."""

        def sql_column(raw_sql):
            return [
                *source("tabToDo"),
                {
                    "type": "sql_column",
                    "new_name": "state",
                    "raw_sql": raw_sql,
                    "data_source": SITE_DB,
                    "data_type": "String",
                },
            ]

        held_back = self.create_chart("held back", sql_column("concat(status, '!')"), "name")
        # a column the reader still has, and a name no table held back
        kept = self.create_chart("kept", sql_column("concat(priority, '!')"), "name")
        unknown = self.create_chart("unknown", sql_column("no_such_column"), "name")

        self.make_status_permlevel()

        with self.assertRaises(NotPermitted) as refusal:
            self.fetch(held_back)
        self.assertEqual(refusal.exception.doctypes, ["ToDo"])

        self.assertEqual([row["name"] for row in self.fetch(kept)["rows"]], [self.todo])
        with self.assertRaises(frappe.db.OperationalError):
            self.fetch(unknown)

    # @feature permissions.not-permitted-chart
    def test_a_sql_column_names_a_held_back_column_in_any_case(self):
        """`InsightsChartv3.fetch` builds a migrated `sql_column`. The database
        reads a column name in any case, so the refusal does too."""
        held_back = self.create_chart(
            "held back upper",
            [
                *source("tabToDo"),
                {
                    "type": "sql_column",
                    "new_name": "state",
                    "raw_sql": "concat(STATUS, '!')",
                    "data_source": SITE_DB,
                    "data_type": "String",
                },
            ],
            "name",
        )

        self.make_status_permlevel()

        with self.assertRaises(NotPermitted) as refusal:
            self.fetch(held_back)
        self.assertEqual(refusal.exception.doctypes, ["ToDo"])

    # @feature permissions.not-permitted-chart
    def test_a_sql_query_that_names_a_held_back_column_is_not_permitted(self):
        """`InsightsChartv3.fetch` builds a SQL query. Each table it names is
        bound to the reader's permitted select, so a held-back column is
        missing there, and is refused as a column an operation names is -
        in any case, and named off the table's alias. A column the reader still
        has, a name the SQL itself defines, and a name no table held back read
        as before."""

        def native(raw_sql):
            return [{"type": "sql", "data_source": SITE_DB, "raw_sql": raw_sql}]

        held_back = [
            self.create_chart(f"native held back {index}", native(raw_sql), "name")
            for index, raw_sql in enumerate(
                (
                    "select name, status from tabToDo",
                    "select t.name from tabToDo t where t.STATUS = 'Open'",
                )
            )
        ]
        kept = self.create_chart("native kept", native("select name, priority from tabToDo"), "name")
        defined = self.create_chart(
            "native defined", native("select name, 'x' as status from tabToDo order by status"), "name"
        )
        unknown = self.create_chart(
            "native unknown", native("select name, no_such_column from tabToDo"), "name"
        )

        self.make_status_permlevel()

        for chart in held_back:
            with self.subTest(chart=chart):
                with self.assertRaises(NotPermitted) as refusal:
                    self.fetch(chart)
                self.assertEqual(refusal.exception.doctypes, ["ToDo"])

        for chart in (kept, defined):
            self.assertEqual([row["name"] for row in self.fetch(chart)["rows"]], [self.todo])
        with self.assertRaises(frappe.db.OperationalError):
            self.fetch(unknown)

    # @feature permissions.not-permitted-chart
    def test_a_union_carries_a_remove_from_either_side(self):
        """`InsightsChartv3.fetch` builds the stored operations. A union keeps
        the columns both sides have, so the other side's remove takes `status`
        off for the author too, and the join's `status` is the right-hand one
        for both of them."""
        self.read_every_row()
        removed = self.create_query(
            "Removed", [*source("tabToDo"), {"type": "remove", "column_names": ["status"]}]
        )
        [source_operation, joined] = self.mutated_status_join()
        union = {"type": "union", "table": {"type": "query", "query_name": removed}, "distinct": True}
        chart = self.create_chart("Union Then Joined", [source_operation, union, joined], "status")
        as_author = self.fetch(chart)
        self.assertNotIn("Open", [row["status"] for row in as_author["rows"]])

        self.make_status_permlevel()

        self.assertEqual(self.fetch(chart)["rows"], as_author["rows"])

    def create_query(self, title, operations) -> str:
        return (
            frappe.get_doc(
                {
                    "doctype": DT.QUERY,
                    "title": f"{PREFIX} {title} {frappe.generate_hash(length=6)}",
                    "workbook": self.workbook,
                    "use_live_connection": 1,
                    "is_builder_query": 1,
                    "operations": operations,
                }
            )
            .insert()
            .name
        )

    def mutated_status_join(self):
        """`tabToDo` joined to a query that carries `status` past the projection.

        A mutate makes the right-hand `status`, so holding back takes it off
        the left side only.
        """
        return [
            *source("tabToDo"),
            {
                "type": "join",
                "join_type": "left",
                "table": {"type": "query", "query_name": self.mutated_status_query()},
                "join_condition": {
                    "left_column": {"type": "column", "column_name": "name"},
                    "right_column": {"type": "column", "column_name": "name"},
                },
                "select_columns": [{"type": "column", "column_name": "status"}],
            },
        ]

    def mutated_status_query(self) -> str:
        """A query over `tabToDo` that carries `status` past the permlevel projection."""
        mutated = frappe.get_doc(
            {
                "doctype": DT.QUERY,
                "title": f"{PREFIX} Mutated Status {frappe.generate_hash(length=6)}",
                "workbook": self.workbook,
                "use_live_connection": 1,
                "is_builder_query": 1,
                "operations": [
                    *source("tabToDo"),
                    {
                        "type": "mutate",
                        "new_name": "status",
                        "data_type": "String",
                        "expression": {"type": "expression", "expression": "priority"},
                    },
                ],
            }
        ).insert()

        return mutated.name

    # @feature permissions.not-permitted-chart
    def test_the_view_answers_with_the_doctypes_the_card_needs(self):
        with as_user(READER), db_connections():
            answer = get_chart_data(self.unreadable_chart)

        self.assertEqual(answer["not_permitted"], {"doctypes": ["Error Log"]})
        self.assertEqual(answer["rows"], [])
        self.assertEqual(answer["columns"], [])

    # @feature permissions.not-permitted-chart
    def test_the_pickers_behind_a_card_answer_a_refusal_too(self):
        """A partly permitted dashboard opens, so its value pickers and ranges
        meet the same refusal. A raw 403 is not something a card can draw."""
        from insights.api.view import get_card_range, get_card_values

        with as_user(READER), db_connections():
            self.assertEqual(get_card_values(self.unreadable_chart, "name", self.partly_board), [])
            self.assertIsNone(get_card_range(self.unreadable_chart, "name", self.partly_board))

    # @feature permissions.not-permitted-chart
    def test_the_builders_own_pickers_answer_what_the_readers_do(self):
        """The builder reaches its filter pickers through `run_doc_method` and a
        reader reaches their twins through `insights.api.view`. One refusal cannot
        have two answers split by which surface asked."""
        board = frappe.get_doc(DT.DASHBOARD, self.partly_board)

        with as_user(READER), db_connections():
            self.assertEqual(board.get_distinct_column_values(REFUSED_FILTER), [])
            self.assertIsNone(board.get_filter_column_range(REFUSED_FILTER))

    # @feature permissions.not-permitted-chart dashboard.filter-values
    def test_a_filter_offers_the_values_of_a_card_behind_a_refused_one(self):
        """A reader's picker calls `view.get_filter_values` and the builder's
        calls the dashboard's twin. The stored links are sorted by chart name,
        so the card the reader is refused may come first - here it does."""
        from insights.api.view import get_filter_range, get_filter_values

        refused = frappe.copy_doc(frappe.get_doc(DT.CHART, self.unreadable_chart))
        refused.insert(set_name="0-refused-first")
        self.addCleanup(frappe.delete_doc, DT.CHART, refused.name, force=True, ignore_permissions=True)
        board = self.create_dashboard(
            "Refused First",
            [refused.name, self.plain_chart],
            links={
                refused.name: f"`{self.unreadable_query}`.`name`",
                self.plain_chart: f"`{frappe.db.get_value(DT.CHART, self.plain_chart, 'query')}`.`name`",
            },
        )
        self.addCleanup(frappe.delete_doc, DT.DASHBOARD, board, force=True, ignore_permissions=True)
        stored = frappe.parse_json(frappe.db.get_value(DT.DASHBOARD, board, "items"))
        self.assertEqual(next(iter(stored[-1]["links"])), refused.name)

        with as_user(READER), db_connections():
            viewed = get_filter_values(board, REFUSED_FILTER)
            built = frappe.get_doc(DT.DASHBOARD, board).get_distinct_column_values(REFUSED_FILTER)
            ranged = get_filter_range(board, REFUSED_FILTER)

        self.assertIn(self.todo, viewed)
        self.assertEqual(sorted(built), sorted(viewed))
        self.assertIsNotNone(ranged)

    # @feature permissions.not-permitted-chart dashboard.filter-values
    def test_a_filter_offers_the_values_of_a_card_behind_a_held_back_column(self):
        """`view.get_filter_values` and `view.get_filter_range` look the column
        up for a reader's picker. A held-back column is refused like a
        table they cannot read, so the next link answers. The card's own picker
        and the builder's query door answer the same refusal."""
        from insights.api.view import get_card_range, get_card_values, get_filter_range, get_filter_values

        permlevel_query = frappe.db.get_value(DT.CHART, self.permlevel_chart, "query")
        refused = frappe.copy_doc(frappe.get_doc(DT.CHART, self.permlevel_chart))
        refused.insert(set_name="0-held-back-column-first")
        self.addCleanup(frappe.delete_doc, DT.CHART, refused.name, force=True, ignore_permissions=True)
        board = self.create_dashboard(
            "Held Back Column First",
            [refused.name, self.plain_chart],
            links={
                refused.name: f"`{permlevel_query}`.`status`",
                self.plain_chart: f"`{frappe.db.get_value(DT.CHART, self.plain_chart, 'query')}`.`name`",
            },
        )
        self.addCleanup(frappe.delete_doc, DT.DASHBOARD, board, force=True, ignore_permissions=True)
        stored = frappe.parse_json(frappe.db.get_value(DT.DASHBOARD, board, "items"))
        self.assertEqual(next(iter(stored[-1]["links"])), refused.name)

        self.make_status_permlevel()

        with as_user(READER), db_connections():
            viewed = get_filter_values(board, REFUSED_FILTER)
            ranged = get_filter_range(board, REFUSED_FILTER)
            card_values = get_card_values(refused.name, "status", board)
            card_range = get_card_range(refused.name, "status", board)
            query = frappe.get_doc(DT.QUERY, permlevel_query)
            query_values = query.get_distinct_column_values("status")
            query_range = query.get_column_range("status")

        self.assertIn(self.todo, viewed)
        self.assertIsNotNone(ranged)
        self.assertEqual(card_values, [])
        self.assertIsNone(card_range)
        self.assertEqual(query_values, [])
        self.assertIsNone(query_range)

    # @feature permissions.not-permitted-chart
    def test_a_refused_drill_is_an_answer_the_dialog_draws(self):
        """The drill dialog draws a refused level, so the refusal comes back as
        an answer like every other endpoint behind an admitted dashboard. Both
        doors answer it: a reader's and the builder's."""
        from insights.api.authoring import get_drill_data as authoring_drill
        from insights.api.view import get_drill_data as view_drill

        level = [{"segment_filters": [], "action": {"rows": True}}]
        config = frappe.parse_json(frappe.db.get_value(DT.CHART, self.unreadable_chart, "config"))

        with as_user(READER), db_connections():
            viewed = view_drill(chart=self.unreadable_chart, dashboard=self.partly_board, drill_stack=level)
            built = authoring_drill(
                query=self.unreadable_query,
                chart_type="Table",
                config=config,
                drill_stack=level,
            )

        for answer in (viewed, built):
            self.assertEqual(answer["not_permitted"], {"doctypes": ["Error Log"]})
            self.assertEqual(answer["rows"], [])
            self.assertEqual(answer["columns"], [])

    # @feature permissions.not-permitted-chart
    def test_the_query_doors_answer_what_their_dashboard_twins_answer(self):
        """The builder's filter dialog calls the query document straight, where
        a reader's picker calls the dashboard's twin. One refusal, one answer,
        whichever surface asked."""
        query = frappe.get_doc(DT.QUERY, self.unreadable_query)

        with as_user(READER), db_connections():
            self.assertEqual(query.get_distinct_column_values("name"), [])
            self.assertIsNone(query.get_column_range("name"))
            self.assertEqual(query.get_columns_for_selection(), [])

    # @feature permissions.not-permitted-chart
    def test_a_row_count_the_reader_may_not_have_is_not_a_zero(self):
        """A count is the one answer whose empty value is a zero, so there is
        nothing for a marker to ride on and "0 rows" would read as an empty
        table."""
        from insights.api.data_sources import get_data_source_table_row_count

        with as_user(READER), db_connections(), self.assertRaises(NotPermitted):
            get_data_source_table_row_count(SITE_DB, UNREADABLE_TABLE)

    # @feature permissions.not-permitted-chart
    def test_a_refusal_that_reaches_the_reader_says_why(self):
        """The table explorer calls `get_data_source_table_row_count` and draws
        the error's message. A refusal leaves the request as a 403, so its
        sentence has to be in the message log frappe answers with - the
        exception's own text is sent only where tracebacks are allowed."""
        from insights.api.data_sources import get_data_source_table_row_count

        frappe.clear_messages()
        with as_user(READER), db_connections(), self.assertRaises(NotPermitted):
            get_data_source_table_row_count(SITE_DB, UNREADABLE_TABLE)

        messages = [message.message for message in frappe.get_message_log()]
        self.assertEqual(messages, ["Needs read access to <strong>Error Log</strong>"])

    # @feature permissions.not-permitted-chart
    def test_a_refusal_the_card_draws_leaves_no_message_beside_it(self):
        """`get_data_source_table` answers the refusal for the explorer's
        preview to draw, so a toast beside it would say the same thing twice."""
        from insights.api.data_sources import get_data_source_table

        frappe.clear_messages()
        with as_user(READER), db_connections():
            get_data_source_table(SITE_DB, UNREADABLE_TABLE)

        self.assertEqual(frappe.get_message_log(), [])

    # @feature permissions.not-permitted-chart
    def test_a_data_source_table_preview_answers_a_refusal(self):
        """The explorer lists a table by the team grant, not by frappe read, so
        clicking one lands here."""
        from insights.api.data_sources import get_data_source_table

        with as_user(READER), db_connections():
            answer = get_data_source_table(SITE_DB, UNREADABLE_TABLE)

        self.assertEqual(answer["not_permitted"], {"doctypes": ["Error Log"]})
        self.assertEqual(answer["rows"], [])


class ADashboardWithNothingPermittedReadsAsNotFound(ContentOverATableTheReaderCannotRead):
    """The same answer as content that does not exist, because there is nothing
    on it this reader may see. A partly permitted one opens, with its Not
    Permitted cards in place, so the layout never shifts."""

    # @feature permissions.not-found-when-nothing-is-permitted
    def test_a_dashboard_every_chart_of_which_is_not_permitted_is_not_found(self):
        with as_user(READER):
            with self.assertRaisesRegex(frappe.DoesNotExistError, "Not Found"):
                get_dashboard(self.refused_board)

    # @feature permissions.not-found-when-nothing-is-permitted
    def test_a_dashboard_every_chart_of_which_is_not_permitted_opens_for_its_writer(self):
        """`view.get_dashboard` through `resolve_for_read`. Not Found is a
        reader's answer; a writer opens the dashboard to fix it."""
        frappe.share.add(DT.WORKBOOK, self.workbook, user=READER, read=1, write=1, notify=0)
        self.addCleanup(frappe.share.add, DT.WORKBOOK, self.workbook, user=READER, read=1, write=0, notify=0)

        with as_user(READER):
            board = get_dashboard(self.refused_board)

        self.assertEqual(board["items"][0]["chart"], self.unreadable_chart)

    # @feature permissions.not-found-when-nothing-is-permitted
    def test_a_dashboard_whose_every_chart_a_user_permission_refuses_opens_for_its_writer(self):
        """`view.get_dashboard`. A User Permission on `Insights Query v3` refuses
        every chart on the board - a chart links its query - and not the
        dashboard, which links only its workbook. The reader gets Not Found; a
        writer opens it, whichever refusal emptied it."""
        other_query = frappe.db.get_value(DT.CHART, self.permlevel_chart, "query")
        permission = frappe.get_doc(
            {"doctype": "User Permission", "user": READER, "allow": DT.QUERY, "for_value": other_query}
        ).insert(ignore_permissions=True)
        self.addCleanup(
            frappe.delete_doc, "User Permission", permission.name, force=True, ignore_permissions=True
        )

        with as_user(READER), self.assertRaisesRegex(frappe.DoesNotExistError, "Not Found"):
            get_dashboard(self.partly_board)

        frappe.share.add(DT.WORKBOOK, self.workbook, user=READER, read=1, write=1, notify=0)
        self.addCleanup(frappe.share.add, DT.WORKBOOK, self.workbook, user=READER, read=1, write=0, notify=0)
        with as_user(READER):
            board = get_dashboard(self.partly_board)

        self.assertTrue(board["can_write"])
        self.assertEqual([item["type"] for item in board["items"]], ["filter"])

    # @feature permissions.not-found-when-nothing-is-permitted permissions.team-grant
    def test_a_dashboard_whose_table_a_team_grants_opens(self):
        """`view.get_dashboard`. On site data a team grant admits a reader as
        desk does, and the card draws for them - so the dashboard is not Not
        Found either."""
        from insights.insights.doctype.insights_table_v3.insights_table_v3 import get_table_name
        from insights.insights.doctype.insights_team.insights_team import clear_cache

        self.set_team_permissions(1)
        table = get_table_name(SITE_DB, UNREADABLE_TABLE)
        if not frappe.db.exists(DT.TABLE, table):
            frappe.get_doc(
                {
                    "doctype": DT.TABLE,
                    "table": UNREADABLE_TABLE,
                    "label": UNREADABLE_TABLE,
                    "data_source": SITE_DB,
                }
            ).insert(ignore_permissions=True)
        team = frappe.get_doc({"doctype": DT.TEAM, "team_name": f"{PREFIX} Team"})
        team.append("team_members", {"user": READER})
        team.append("team_permissions", {"resource_type": DT.TABLE, "resource_name": table})
        team.insert(ignore_permissions=True)
        self.addCleanup(clear_cache)
        self.addCleanup(frappe.delete_doc, DT.TEAM, team.name, force=True, ignore_permissions=True)
        clear_cache()

        with as_user(READER):
            board = get_dashboard(self.refused_board)

        self.assertEqual(board["items"][0]["chart"], self.unreadable_chart)

    # @feature permissions.not-found-when-nothing-is-permitted
    def test_a_dashboard_whose_table_desk_shares_one_document_of_opens(self):
        """`view.get_dashboard`. A share is desk's read too - the engine reads
        the shared rows through `frappe.get_list` - so a reader with no role on
        the doctype but one shared document draws a card."""
        log = frappe.get_doc({"doctype": "Error Log", "method": f"{PREFIX} shared"}).insert(
            ignore_permissions=True
        )
        self.addCleanup(frappe.delete_doc, "Error Log", log.name, force=True, ignore_permissions=True)
        frappe.share.add(
            "Error Log", log.name, user=READER, read=1, notify=0, flags={"ignore_share_permission": True}
        )

        with as_user(READER):
            board = get_dashboard(self.refused_board)

        self.assertEqual(board["items"][0]["chart"], self.unreadable_chart)

    # @feature permissions.not-found-when-nothing-is-permitted
    def test_a_dashboard_with_one_permitted_chart_opens_whole(self):
        with as_user(READER):
            board = get_dashboard(self.partly_board)

        self.assertEqual(
            [item["chart"] for item in board["items"] if item["type"] == "chart"],
            [self.unreadable_chart, self.plain_chart],
        )

    # @feature permissions.not-found-when-nothing-is-permitted
    def test_a_dashboard_whose_charts_are_not_configured_yet_opens(self):
        """A chart that names no query refuses nobody, so it cannot read the
        dashboard as Not Found - for its own owner either."""
        unconfigured = frappe.get_doc(
            {
                "doctype": DT.CHART,
                "title": f"{PREFIX} Unconfigured",
                "workbook": self.workbook,
                "chart_type": "Bar",
                "config": {},
            }
        ).insert()
        board = self.create_dashboard("Unconfigured", [unconfigured.name])

        self.assertEqual(get_dashboard(board)["items"][0]["chart"], unconfigured.name)
        with as_user(READER):
            self.assertEqual(get_dashboard(board)["items"][0]["chart"], unconfigured.name)

    # @feature permissions.not-found-when-nothing-is-permitted
    def test_a_dashboard_with_no_charts_at_all_opens(self):
        empty = self.create_dashboard("Empty", [])

        with as_user(READER):
            self.assertEqual(get_dashboard(empty)["items"], [])
