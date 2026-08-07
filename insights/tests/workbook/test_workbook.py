import frappe

from insights.api.workbooks import (
    create_folder,
    delete_folder,
    get_share_permissions,
    get_workbooks,
    import_workbook,
    update_share_permissions,
    update_sort_orders,
)
from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import DT, USER_1, create_test_user, delete_users
from insights.tests.workbook_utils import (
    cleanup_test_workbooks,
    create_workbook_with_content,
    get_doc,
    get_workbook,
    run_doc_method,
)

COLLABORATOR = "workbook_flow_collaborator@test.com"


class TestWorkbook(InsightsIntegrationTestCase):
    COMMIT_AFTER_TEST_SETUP = True
    COMMIT_AFTER_TEST_TEARDOWN = True

    @classmethod
    def before_class(cls):
        cleanup_test_workbooks(USER_1, COLLABORATOR)
        delete_users(USER_1, COLLABORATOR)
        create_test_user(USER_1)
        create_test_user(COLLABORATOR)

    @classmethod
    def after_class(cls):
        cleanup_test_workbooks(USER_1, COLLABORATOR)
        delete_users(USER_1, COLLABORATOR)

    def before_test(self):
        cleanup_test_workbooks(USER_1, COLLABORATOR)

    def after_test(self):
        cleanup_test_workbooks(USER_1, COLLABORATOR)

    def test_owner_can_build_workbook_query_chart_dashboard_flow(self):
        content = create_workbook_with_content(USER_1, "Workbook Flow Test Authoring")

        with self.as_user(USER_1):
            workbook = get_workbook(content["workbook"].name)
            chart = get_doc(DT.CHART, content["chart"].name)
            dashboard = get_doc(DT.DASHBOARD, content["dashboard"].name)
            query_result = run_doc_method("execute", get_doc(DT.QUERY, content["query"].name))
        dashboard_items = frappe.parse_json(dashboard["items"]) or []

        self.assertEqual([row["name"] for row in workbook["queries"]], [content["query"].name])
        self.assertEqual([row["name"] for row in workbook["charts"]], [content["chart"].name])
        self.assertEqual([row["name"] for row in workbook["dashboards"]], [content["dashboard"].name])

        self.assertIn("sql", query_result)
        self.assertGreater(len(query_result["columns"]), 0)
        self.assertEqual(chart["query"], content["query"].name)
        self.assertTrue(any(item.get("chart") == content["chart"].name for item in dashboard_items))

    def test_deleting_workbook_removes_the_user_visible_tree(self):
        content = create_workbook_with_content(USER_1, "Workbook Flow Test Delete")

        with self.as_user("Administrator"):
            frappe.delete_doc(DT.WORKBOOK, content["workbook"].name, force=True)

        self.assertFalse(frappe.db.exists(DT.WORKBOOK, content["workbook"].name))
        self.assertFalse(frappe.db.exists(DT.QUERY, content["query"].name))
        self.assertFalse(frappe.db.exists(DT.CHART, content["chart"].name))
        self.assertFalse(frappe.db.exists(DT.DASHBOARD, content["dashboard"].name))

    def test_owner_can_organize_and_reorder_workbook_contents(self):
        content = create_workbook_with_content(
            USER_1,
            "Workbook Flow Test Organization",
            include_secondary_items=True,
        )

        with self.as_user(USER_1):
            query_folder = create_folder(
                content["workbook"].name,
                "Workbook Flow Test Organization Query Folder",
                "query",
            )
            chart_folder = create_folder(
                content["workbook"].name,
                "Workbook Flow Test Organization Chart Folder",
                "chart",
            )
            update_sort_orders(
                content["workbook"].name,
                [
                    {"type": "folder", "name": chart_folder, "sort_order": 0},
                    {"type": "folder", "name": query_folder, "sort_order": 1},
                    {
                        "type": "query",
                        "name": content["secondary_query"].name,
                        "sort_order": 0,
                        "folder": None,
                    },
                    {
                        "type": "query",
                        "name": content["query"].name,
                        "sort_order": 1,
                        "folder": query_folder,
                    },
                    {
                        "type": "chart",
                        "name": content["secondary_chart"].name,
                        "sort_order": 0,
                        "folder": None,
                    },
                    {
                        "type": "chart",
                        "name": content["chart"].name,
                        "sort_order": 1,
                        "folder": chart_folder,
                    },
                ],
            )
            workbook = get_workbook(content["workbook"].name)

        self.assertEqual([row["name"] for row in workbook["folders"]], [chart_folder, query_folder])
        self.assertEqual(
            [row["name"] for row in workbook["queries"]],
            [content["secondary_query"].name, content["query"].name],
        )
        self.assertEqual(
            [row["name"] for row in workbook["charts"]],
            [content["secondary_chart"].name, content["chart"].name],
        )
        self.assertEqual(workbook["queries"][1]["folder"], query_folder)
        self.assertEqual(workbook["charts"][1]["folder"], chart_folder)

        with self.as_user(USER_1):
            delete_folder(query_folder, move_items_to_root=True)
            delete_folder(chart_folder, move_items_to_root=True)
            workbook = get_workbook(content["workbook"].name)

        self.assertEqual(workbook["folders"], [])
        self.assertTrue(all(not row["folder"] for row in workbook["queries"]))
        self.assertTrue(all(not row["folder"] for row in workbook["charts"]))

    def test_duplicate_workbook_preserves_a_usable_copy(self):
        content = create_workbook_with_content(
            USER_1,
            "Workbook Flow Test Duplicate",
            include_folders=True,
        )

        with self.as_user(USER_1):
            original_workbook = get_workbook(content["workbook"].name)
            duplicate_name = run_doc_method(
                "duplicate",
                get_doc(DT.WORKBOOK, content["workbook"].name),
            )
            duplicate_workbook = get_workbook(duplicate_name)
        duplicate_query_name = duplicate_workbook["queries"][0]["name"]
        duplicate_chart_name = duplicate_workbook["charts"][0]["name"]
        with self.as_user(USER_1):
            duplicate_chart = get_doc(DT.CHART, duplicate_chart_name)
            duplicate_dashboard = get_doc(
                DT.DASHBOARD,
                duplicate_workbook["dashboards"][0]["name"],
            )
        duplicate_dashboard_items = frappe.parse_json(duplicate_dashboard["items"]) or []
        with self.as_user(USER_1):
            duplicate_result = run_doc_method("execute", get_doc(DT.QUERY, duplicate_query_name))

        self.assertEqual(len(duplicate_workbook["folders"]), 2)
        self.assertEqual(len(duplicate_workbook["queries"]), 1)
        self.assertEqual(len(duplicate_workbook["charts"]), 1)
        self.assertEqual(len(duplicate_workbook["dashboards"]), 1)
        self.assertNotEqual(duplicate_query_name, content["query"].name)
        self.assertEqual(duplicate_chart["query"], duplicate_query_name)
        self.assertTrue(any(item.get("chart") == duplicate_chart_name for item in duplicate_dashboard_items))
        self.assertTrue(
            {row["name"] for row in duplicate_workbook["folders"]}.isdisjoint(
                {row["name"] for row in original_workbook["folders"]}
            )
        )
        self.assertIn(
            duplicate_workbook["queries"][0]["folder"], {row["name"] for row in duplicate_workbook["folders"]}
        )
        self.assertIn(
            duplicate_workbook["charts"][0]["folder"], {row["name"] for row in duplicate_workbook["folders"]}
        )
        self.assertGreater(len(duplicate_result["columns"]), 0)

    def test_export_and_import_preserve_a_usable_workflow(self):
        content = create_workbook_with_content(
            USER_1,
            "Workbook Flow Test Import",
            include_folders=True,
        )

        with self.as_user(USER_1):
            original_workbook = get_workbook(content["workbook"].name)
            exported_workbook = run_doc_method(
                "export",
                get_doc(DT.WORKBOOK, content["workbook"].name),
            )
            imported_name = import_workbook(exported_workbook)
            imported_workbook = get_workbook(imported_name)
        imported_query_name = imported_workbook["queries"][0]["name"]
        imported_chart_name = imported_workbook["charts"][0]["name"]
        with self.as_user(USER_1):
            imported_chart = get_doc(DT.CHART, imported_chart_name)
            imported_dashboard = get_doc(
                DT.DASHBOARD,
                imported_workbook["dashboards"][0]["name"],
            )
        imported_dashboard_items = frappe.parse_json(imported_dashboard["items"]) or []
        with self.as_user(USER_1):
            imported_result = run_doc_method("execute", get_doc(DT.QUERY, imported_query_name))

        self.assertEqual(len(imported_workbook["folders"]), 2)
        self.assertEqual(len(imported_workbook["queries"]), 1)
        self.assertEqual(len(imported_workbook["charts"]), 1)
        self.assertEqual(len(imported_workbook["dashboards"]), 1)
        self.assertNotEqual(imported_query_name, content["query"].name)
        self.assertEqual(imported_chart["query"], imported_query_name)
        self.assertTrue(any(item.get("chart") == imported_chart_name for item in imported_dashboard_items))
        self.assertTrue(
            {row["name"] for row in imported_workbook["folders"]}.isdisjoint(
                {row["name"] for row in original_workbook["folders"]}
            )
        )
        self.assertIn(
            imported_workbook["queries"][0]["folder"], {row["name"] for row in imported_workbook["folders"]}
        )
        self.assertIn(
            imported_workbook["charts"][0]["folder"], {row["name"] for row in imported_workbook["folders"]}
        )
        self.assertGreater(len(imported_result["columns"]), 0)

    def test_shared_workbook_supports_read_only_public_access_but_blocks_structure_changes(self):
        content = create_workbook_with_content(USER_1, "Workbook Flow Test Shared")

        with self.as_user(USER_1):
            run_doc_method("track_view", get_doc(DT.WORKBOOK, content["workbook"].name))
            update_share_permissions(content["workbook"].name, [], organization_access="view")
            share_permissions = get_share_permissions(content["workbook"].name)
            owner_workbooks = get_workbooks(search_term="Workbook Flow Test Shared")

        self.assertEqual(share_permissions["organization_access"], "view")
        self.assertEqual(
            {permission["user"] for permission in share_permissions["user_permissions"]},
            {USER_1},
        )
        self.assertEqual(len(owner_workbooks), 1)
        self.assertEqual(owner_workbooks[0]["name"], content["workbook"].name)
        self.assertEqual(owner_workbooks[0]["views"], 1)
        self.assertTrue(owner_workbooks[0]["shared_with_organization"])

        with self.as_user(COLLABORATOR):
            collaborator_workbooks = get_workbooks(search_term="Workbook Flow Test Shared")
            workbook = get_workbook(content["workbook"].name)
            query = get_doc(DT.QUERY, content["query"].name)
            chart = get_doc(DT.CHART, content["chart"].name)
            dashboard = get_doc(DT.DASHBOARD, content["dashboard"].name)

        self.assertEqual([row["name"] for row in collaborator_workbooks], [content["workbook"].name])
        self.assertTrue(workbook["read_only"])
        self.assertTrue(query["read_only"])
        self.assertTrue(chart["read_only"])
        self.assertTrue(dashboard["read_only"])
        self.assertEqual([row["name"] for row in workbook["queries"]], [content["query"].name])
        self.assertEqual([row["name"] for row in workbook["charts"]], [content["chart"].name])
        self.assertEqual([row["name"] for row in workbook["dashboards"]], [content["dashboard"].name])

        with self.as_user(COLLABORATOR):
            with self.assertRaises(frappe.PermissionError):
                create_folder(content["workbook"].name, "Blocked Query Folder", "query")

            with self.assertRaises(frappe.PermissionError):
                update_sort_orders(
                    content["workbook"].name,
                    [
                        {
                            "type": "query",
                            "name": content["query"].name,
                            "sort_order": 0,
                            "folder": None,
                        }
                    ],
                )
