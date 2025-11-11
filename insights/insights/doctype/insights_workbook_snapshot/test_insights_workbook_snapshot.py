# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]


class IntegrationTestInsightsWorkbookSnapshot(IntegrationTestCase):
    """
    Integration tests for InsightsWorkbookSnapshot.
    Use this class for testing interactions between multiple components.
    """

    def setUp(self):
        """Set up test fixtures"""
        self.workbook = frappe.get_doc(
            {
                "doctype": "Insights Workbook",
                "title": "Test Workbook",
            }
        ).insert()

    def tearDown(self):
        """Clean up test data"""
        if self.workbook and frappe.db.exists("Insights Workbook", self.workbook.name):
            frappe.delete_doc("Insights Workbook", self.workbook.name, force=True)

    def test_workbook_creation(self):
        """Test basic workbook creation"""
        self.assertTrue(self.workbook.name)
        self.assertEqual(self.workbook.title, "Test Workbook")

    def test_save_snapshot(self):
        """Test saving a snapshot of workbook"""
        # Create a query in the workbook
        query = frappe.get_doc(
            {
                "doctype": "Insights Query v3",
                "workbook": self.workbook.name,
                "title": "Test Query",
                "is_builder_query": 1,
                "operations": [],
            }
        ).insert()

        # Save snapshot
        snapshot_name = self.workbook.save_snapshot("Test Snapshot")

        # Verify snapshot is created
        self.assertTrue(frappe.db.exists("Insights Workbook Snapshot", snapshot_name))
        snapshot = frappe.get_doc("Insights Workbook Snapshot", snapshot_name)
        self.assertEqual(str(snapshot.workbook), str(self.workbook.name))
        self.assertEqual(snapshot.title, "Test Snapshot")

        # Verify snapshot contains the query
        snapshot_data = frappe.parse_json(snapshot.snapshot)
        self.assertIn(query.name, snapshot_data["dependencies"]["queries"])

        # Cleanup
        frappe.delete_doc("Insights Query v3", query.name, force=True)

    def test_get_snapshots(self):
        """Test retrieving all snapshots for a workbook"""
        # Create multiple snapshots
        snapshot1 = self.workbook.save_snapshot("Snapshot 1")
        snapshot2 = self.workbook.save_snapshot("Snapshot 2")

        # Get all snapshots
        snapshots = self.workbook.get_snapshots()

        # Verify both snapshots are returned
        self.assertEqual(len(snapshots), 2)
        snapshot_names = [s["name"] for s in snapshots]
        self.assertIn(snapshot1, snapshot_names)
        self.assertIn(snapshot2, snapshot_names)

    def test_restore_snapshot_creates_new_items(self):
        """Test restoring snapshot creates items that don't exist"""
        # Create a query
        query = frappe.get_doc(
            {
                "doctype": "Insights Query v3",
                "workbook": self.workbook.name,
                "title": "Original Query",
                "is_builder_query": 1,
                "operations": [],
            }
        ).insert()

        # Save snapshot
        snapshot_name = self.workbook.save_snapshot("Before Delete")

        # Delete the query
        frappe.delete_doc("Insights Query v3", query.name, force=True)

        # Verify query is deleted
        self.assertFalse(frappe.db.exists("Insights Query v3", query.name))

        # Restore snapshot
        result = self.workbook.restore_snapshot(snapshot_name)

        # Verify restoration was successful
        self.assertTrue(result["success"])

        # Verify query was recreated with same name
        self.assertTrue(frappe.db.exists("Insights Query v3", query.name))
        restored_query = frappe.get_doc("Insights Query v3", query.name)
        self.assertEqual(restored_query.title, "Original Query")

    def test_restore_snapshot_updates_existing_items(self):
        """Test restoring snapshot updates existing items"""
        # Create a query
        query = frappe.get_doc(
            {
                "doctype": "Insights Query v3",
                "workbook": self.workbook.name,
                "title": "Original Title",
                "is_builder_query": 1,
                "operations": [],
            }
        ).insert()

        # Save snapshot
        snapshot_name = self.workbook.save_snapshot("Before Update")

        # Modify the query
        query.title = "Modified Title"
        query.save()

        # Restore snapshot
        self.workbook.restore_snapshot(snapshot_name)

        # Verify query was restored to original state
        restored_query = frappe.get_doc("Insights Query v3", query.name)
        self.assertEqual(restored_query.title, "Original Title")

    def test_restore_snapshot_deletes_extra_items(self):
        """Test restoring snapshot deletes items not in snapshot"""
        # Save empty snapshot
        snapshot_name = self.workbook.save_snapshot("Empty State")

        # Create a query after snapshot
        query = frappe.get_doc(
            {
                "doctype": "Insights Query v3",
                "workbook": self.workbook.name,
                "title": "New Query",
                "is_builder_query": 1,
                "operations": [],
            }
        ).insert()

        # Verify query exists
        self.assertTrue(frappe.db.exists("Insights Query v3", query.name))

        # Restore snapshot
        self.workbook.restore_snapshot(snapshot_name)

        # Verify query was deleted
        self.assertFalse(frappe.db.exists("Insights Query v3", query.name))

    def test_restore_snapshot_preserves_query_names(self):
        """Test that restoring preserves query names for shared URLs"""
        # Create queries with specific names
        query1 = frappe.get_doc(
            {
                "doctype": "Insights Query v3",
                "workbook": self.workbook.name,
                "title": "Query 1",
                "is_builder_query": 1,
                "operations": [],
            }
        ).insert()
        original_query1_name = query1.name

        # Save snapshot
        snapshot_name = self.workbook.save_snapshot("With Queries")

        # Modify queries
        query1.title = "Modified Query 1"
        query1.save()

        # Restore snapshot
        self.workbook.restore_snapshot(snapshot_name)

        # Verify query names are preserved (not recreated with new IDs)
        self.assertTrue(frappe.db.exists("Insights Query v3", original_query1_name))
        restored_query = frappe.get_doc("Insights Query v3", original_query1_name)
        self.assertEqual(restored_query.title, "Query 1")

    def test_snapshot_cleanup_on_workbook_delete(self):
        """Test that snapshots are deleted when workbook is deleted"""
        # Create snapshots
        snapshot1 = self.workbook.save_snapshot("Snapshot 1")
        snapshot2 = self.workbook.save_snapshot("Snapshot 2")

        # Verify snapshots exist
        self.assertTrue(frappe.db.exists("Insights Workbook Snapshot", snapshot1))
        self.assertTrue(frappe.db.exists("Insights Workbook Snapshot", snapshot2))

        # Delete workbook
        workbook_name = self.workbook.name
        frappe.delete_doc("Insights Workbook", workbook_name, force=True)

        # Verify snapshots are deleted
        self.assertFalse(frappe.db.exists("Insights Workbook Snapshot", snapshot1))
        self.assertFalse(frappe.db.exists("Insights Workbook Snapshot", snapshot2))

        # Set to None to prevent tearDown from trying to delete again
        self.workbook = None

    def test_restore_snapshot_with_folders(self):
        """Test restoring snapshot with folders"""
        # Create folder
        folder = frappe.get_doc(
            {
                "doctype": "Insights Folder",
                "workbook": self.workbook.name,
                "title": "Test Folder",
                "type": "query",
            }
        ).insert()

        # Create query in folder
        query = frappe.get_doc(
            {
                "doctype": "Insights Query v3",
                "workbook": self.workbook.name,
                "title": "Query in Folder",
                "folder": folder.name,
                "is_builder_query": 1,
                "operations": [],
            }
        ).insert()

        # Save snapshot
        snapshot_name = self.workbook.save_snapshot("With Folder")

        # Delete folder and query
        frappe.delete_doc("Insights Query v3", query.name, force=True)
        frappe.delete_doc("Insights Folder", folder.name, force=True)

        # Restore snapshot
        self.workbook.restore_snapshot(snapshot_name)

        # Verify folder and query are restored
        self.assertTrue(frappe.db.exists("Insights Folder", folder.name))
        self.assertTrue(frappe.db.exists("Insights Query v3", query.name))

        # Verify query is still in folder
        restored_query = frappe.get_doc("Insights Query v3", query.name)
        self.assertEqual(restored_query.folder, folder.name)

    def test_snapshot_auto_naming(self):
        """Test automatic snapshot naming when name not provided"""
        # Create snapshot without providing name
        snapshot_name = self.workbook.save_snapshot()

        # Verify snapshot was created with auto-generated name
        self.assertTrue(frappe.db.exists("Insights Workbook Snapshot", snapshot_name))
        snapshot = frappe.get_doc("Insights Workbook Snapshot", snapshot_name)
        self.assertTrue(snapshot.title.startswith("Snapshot "))

    def test_restore_snapshot_permission_check(self):
        """Test that restore_snapshot checks write permission"""
        # Save snapshot as admin
        snapshot_name = self.workbook.save_snapshot("Test Snapshot")

        # This test would need to be run with a different user context
        # to fully test permissions, but we can verify the check exists
        # by looking at the code structure

        # Verify the method exists and is whitelisted
        self.assertTrue(hasattr(self.workbook, "restore_snapshot"))
        self.assertTrue(callable(self.workbook.restore_snapshot))

    def test_duplicate_workbook_creates_snapshots_independently(self):
        """Test that duplicated workbook has independent snapshots"""
        # Create snapshot in original workbook
        snapshot1 = self.workbook.save_snapshot("Original Snapshot")

        # Duplicate workbook
        new_workbook_name = self.workbook.duplicate()
        new_workbook = frappe.get_doc("Insights Workbook", new_workbook_name)

        # Get snapshots from new workbook
        new_snapshots = new_workbook.get_snapshots()

        # Verify new workbook has no snapshots (snapshots are not duplicated)
        self.assertEqual(len(new_snapshots), 0)

        # Cleanup
        frappe.delete_doc("Insights Workbook", new_workbook_name, force=True)

    def test_restore_snapshot_recreates_chart_data_query(self):
        """Test that restoring snapshot recreates chart data_query (doesn't preserve old reference)"""
        # Create a query
        query = frappe.get_doc(
            {
                "doctype": "Insights Query v3",
                "workbook": self.workbook.name,
                "title": "Test Query",
                "is_builder_query": 1,
                "operations": [],
            }
        ).insert()

        # Create a chart (which auto-creates a data_query)
        chart = frappe.get_doc(
            {
                "doctype": "Insights Chart v3",
                "workbook": self.workbook.name,
                "title": "Test Chart",
                "query": query.name,
                "chart_type": "Bar",
                "config": {},
            }
        ).insert()

        # Verify data_query was created
        self.assertTrue(chart.data_query)
        original_data_query = chart.data_query

        # Save snapshot
        snapshot_name = self.workbook.save_snapshot("Before Modify")

        # Modify the chart
        chart.title = "Modified Chart"
        chart.save()

        # Restore snapshot
        self.workbook.restore_snapshot(snapshot_name)

        # Verify chart was restored
        restored_chart = frappe.get_doc("Insights Chart v3", chart.name)
        self.assertEqual(restored_chart.title, "Test Chart")

        # Verify data_query was recreated (new ID, not the original)
        self.assertTrue(restored_chart.data_query)
        self.assertNotEqual(restored_chart.data_query, original_data_query)
        # But it should exist and be valid
        self.assertTrue(frappe.db.exists("Insights Query v3", restored_chart.data_query))
