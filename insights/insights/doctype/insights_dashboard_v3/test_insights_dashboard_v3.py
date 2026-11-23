# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from insights.insights.doctype.insights_workbook.insights_workbook import import_workbook
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import (
    DT,
    create_test_chart,
    create_test_workbook,
    delete_users,
    delete_workbooks,
)
from insights.tests.permissions_utils import USER_1, create_test_users

OWNER = USER_1
WORKBOOK_TITLE = "Dashboard Layout Ids"


def text(i):
    item = {"type": "text", "text": f"<p>{i}</p>"}
    if i:
        item["layout"] = {"i": i, "x": 0, "y": 0, "w": 4, "h": 4}
    return item


class TestDashboardLayoutIds(InsightsIntegrationTestCase):
    @classmethod
    def before_class(cls):
        create_test_users()
        cls.workbook = create_test_workbook(OWNER, title=WORKBOOK_TITLE).name

    @classmethod
    def after_class(cls):
        delete_workbooks(title_prefix=WORKBOOK_TITLE)
        delete_users(OWNER)

    def insert(self, items, workbook=None):
        with self.as_user(OWNER):
            return frappe.get_doc(
                {
                    "doctype": DT.DASHBOARD,
                    "title": "Layout Ids",
                    "workbook": workbook or self.workbook,
                    "items": items,
                }
            ).insert()

    def save(self, name, items):
        with self.as_user(OWNER):
            dashboard = frappe.get_doc(DT.DASHBOARD, name)
            dashboard.items = items
            return dashboard.save()

    def stored_layouts(self, name):
        return [
            item.get("layout") for item in frappe.parse_json(frappe.db.get_value(DT.DASHBOARD, name, "items"))
        ]

    # @feature dashboard.item-layout-ids
    def test_an_item_with_no_layout_gets_the_cell_the_editor_gives_it_below_the_others(self):
        placed, unplaced = self.stored_layouts(self.insert([text("a"), text(None)]).name)

        self.assertEqual(placed, text("a")["layout"])
        self.assertNotIn(unplaced.pop("i"), (None, "a"))
        self.assertEqual(unplaced, {"x": 0, "y": 4, "w": 10, "h": 5})

    # @feature dashboard.item-layout-ids
    def test_an_item_with_a_layout_but_no_id_keeps_its_cell(self):
        box = {"x": 2, "y": 3, "w": 5, "h": 6}

        (layout,) = self.stored_layouts(self.insert([{**text(None), "layout": dict(box)}]).name)

        self.assertTrue(layout.pop("i"))
        self.assertEqual(layout, box)

    # @feature dashboard.item-layout-ids
    def test_an_item_with_part_of_a_layout_gets_the_rest_of_the_cell(self):
        dashboard = self.insert(
            [text("a"), {**text(None), "layout": {"x": 3}}, {**text("c"), "layout": {"i": "c"}}]
        )

        placed, part, id_only = self.stored_layouts(dashboard.name)

        self.assertEqual(placed, text("a")["layout"])
        self.assertTrue(part.pop("i"))
        self.assertEqual(part, {"x": 3, "y": 4, "w": 10, "h": 5})
        self.assertEqual(id_only, {"i": "c", "x": 0, "y": 9, "w": 10, "h": 5})

    # @feature dashboard.item-layout-ids
    def test_a_layout_the_grid_cannot_read_gets_a_cell_of_its_own(self):
        unreadable = {**text(None), "layout": "abc"}
        string_y = {**text("b"), "layout": {"i": "b", "x": 0, "y": "3", "w": 4, "h": 4}}

        first, second = self.stored_layouts(self.insert([unreadable, string_y]).name)

        self.assertTrue(first.pop("i"))
        self.assertEqual(first, {"x": 0, "y": 0, "w": 10, "h": 5})
        self.assertEqual(second, {"i": "b", "x": 0, "y": 5, "w": 4, "h": 4})

    # @feature dashboard.item-layout-ids
    def test_a_number_chart_gets_the_width_of_one_card(self):
        number = create_test_chart(OWNER, self.workbook, chart_type="Number").name
        bar = create_test_chart(OWNER, self.workbook).name

        number_cell, bar_cell = self.stored_layouts(
            self.insert([{"type": "chart", "chart": number}, {"type": "chart", "chart": bar}]).name
        )

        self.assertEqual((number_cell["w"], number_cell["h"]), (4, 4))
        self.assertEqual((bar_cell["w"], bar_cell["h"]), (10, 20))

    # @feature dashboard.item-layout-ids
    def test_a_repeated_layout_id_gives_the_later_item_a_new_one(self):
        first, repeat = self.stored_layouts(self.insert([text("a"), text("a")]).name)

        self.assertEqual(first, text("a")["layout"])
        self.assertNotIn(repeat.pop("i"), (None, "a"))
        self.assertEqual(repeat, {"x": 0, "y": 0, "w": 4, "h": 4})

    # @feature dashboard.item-layout-ids
    def test_a_workbook_whose_dashboard_stores_a_repeated_id_duplicates(self):
        workbook = create_test_workbook(OWNER, title=f"{WORKBOOK_TITLE} Duplicate").name
        dashboard = self.insert([text("a")], workbook).name
        frappe.db.set_value(DT.DASHBOARD, dashboard, "items", frappe.as_json([text("a"), text("a")]))

        with self.as_user(OWNER):
            copy = frappe.get_doc(DT.WORKBOOK, workbook).duplicate()
        self.addCleanup(frappe.delete_doc, DT.WORKBOOK, copy, force=True)

        (copied,) = frappe.get_all(DT.DASHBOARD, filters={"workbook": copy}, pluck="name")
        ids = [layout["i"] for layout in self.stored_layouts(copied)]
        self.assertEqual(ids[0], "a")
        self.assertEqual(len(set(ids)), 2)

    # @feature dashboard.item-layout-ids
    def test_an_imported_dashboard_with_a_repeated_layout_id_imports(self):
        with self.as_user(OWNER):
            exported = frappe.get_doc(DT.WORKBOOK, self.workbook).export()
            exported["title"] = f"{WORKBOOK_TITLE} Import"
            exported["dashboards"] = {
                "imported": {"name": "imported", "title": "Imported", "items": [text("a"), text("a")]}
            }
            workbook = import_workbook(exported)["workbook"]

        (imported,) = frappe.get_all(
            DT.DASHBOARD, filters={"workbook": workbook, "title": "Imported"}, pluck="name"
        )
        ids = [layout["i"] for layout in self.stored_layouts(imported)]
        self.assertEqual(ids[0], "a")
        self.assertEqual(len(set(ids)), 2)
