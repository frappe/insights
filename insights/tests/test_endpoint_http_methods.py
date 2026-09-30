"""An endpoint that keeps a write under GET accepts only POST.

`InsightsIntegrationTestCase` watches every test for such an endpoint. These
tests pin what the watch reports. The watch sees only what the tests run, so a
new endpoint also has to be listed here before it may accept GET.
"""

import importlib
import pkgutil

import frappe
from frappe.tests import UnitTestCase

import insights
from insights.decorators import insights_whitelist
from insights.tests.base import InsightsIntegrationTestCase

# An endpoint here was never checked for writes. Take it off the list once it
# accepts only POST, or once it is read and found to keep no write under GET.
ENDPOINTS_ACCEPTING_GET = [
    "insights.api.alerts.get_alerts",
    "insights.api.dashboards.add_chart_to_dashboard",
    "insights.api.dashboards.create_dashboard",
    "insights.api.dashboards.get_dashboard_list",
    "insights.api.dashboards.get_dashboard_options",
    "insights.api.dashboards.get_dashboards",
    "insights.api.dashboards.get_recent_dashboards",
    "insights.api.data_sources.create_data_source",
    "insights.api.data_sources.create_table_link",
    "insights.api.data_sources.delete_data_source",
    "insights.api.data_sources.fetch_column_values",
    "insights.api.data_sources.get_all_data_sources",
    "insights.api.data_sources.get_columns_from_uploaded_file",
    "insights.api.data_sources.get_data_source_table",
    "insights.api.data_sources.get_data_source_table_columns",
    "insights.api.data_sources.get_data_source_table_row_count",
    "insights.api.data_sources.get_data_source_tables",
    "insights.api.data_sources.get_data_sources",
    "insights.api.data_sources.get_data_sources_of_tables",
    "insights.api.data_sources.get_relation",
    "insights.api.data_sources.get_schema",
    "insights.api.data_sources.get_table_columns",
    "insights.api.data_sources.get_table_links",
    "insights.api.data_sources.get_table_name",
    "insights.api.data_sources.get_tables",
    "insights.api.data_sources.import_csv",
    "insights.api.data_sources.test_connection",
    "insights.api.data_sources.update_table_links",
    "insights.api.data_store.get_data_store_tables",
    "insights.api.get_app_version",
    "insights.api.get_doc",
    "insights.api.get_file_data",
    "insights.api.get_security_update",
    "insights.api.get_site_info",
    "insights.api.get_user_info",
    "insights.api.home.create_last_viewed_log",
    "insights.api.home.get_last_viewed_records",
    "insights.api.maps.find_unresolved_regions",
    "insights.api.maps.get_available_regions",
    "insights.api.maps.save_region_mappings",
    "insights.api.notebooks.create_notebook",
    "insights.api.notebooks.create_notebook_page",
    "insights.api.notebooks.get_notebook_pages",
    "insights.api.notebooks.get_notebooks",
    "insights.api.permissions.get_resource_access_info",
    "insights.api.permissions.grant_access",
    "insights.api.permissions.revoke_access",
    "insights.api.public.fetch_column_values_public",
    "insights.api.public.get_public_chart",
    "insights.api.public.get_public_dashboard",
    "insights.api.public.get_public_dashboard_chart_data",
    "insights.api.public.get_public_key",
    "insights.api.queries.create_chart",
    "insights.api.queries.create_query",
    "insights.api.queries.get_queries",
    "insights.api.queries.pivot",
    "insights.api.run_doc_method",
    "insights.api.setup.add_database",
    "insights.api.setup.complete_setup",
    "insights.api.setup.setup_complete",
    "insights.api.setup.setup_sample_data",
    "insights.api.setup.submit_survey_responses",
    "insights.api.setup.test_database_connection",
    "insights.api.setup.update_erpnext_source_title",
    "insights.api.shared.get_chart_name",
    "insights.api.shared.get_dashboard_name",
    "insights.api.templates.get_workbook_templates",
    "insights.api.translations.get_translations",
    "insights.api.update_default_version",
    "insights.api.user.accept_invitation",
    "insights.api.user.add_insights_user",
    "insights.api.user.create_team",
    "insights.api.user.delete_team",
    "insights.api.user.get_teams",
    "insights.api.user.get_users",
    "insights.api.user.update_team",
    "insights.api.user.update_user",
    "insights.api.v2_migration.get_v2_dashboards",
    "insights.api.v2_migration.get_v2_migration_nudge",
    "insights.api.v2_migration.get_v2_migration_status",
    "insights.api.v2_migration.get_v2_verification",
    "insights.api.v2_migration.migrate_v2_dashboards",
    "insights.api.v2_migration.preview_v2_dashboard",
    "insights.api.v2_migration.scan_v2_dashboards",
    "insights.api.v2_migration.set_v2_migration_nudge",
    "insights.api.workbooks.create_folder",
    "insights.api.workbooks.delete_folder",
    "insights.api.workbooks.get_share_permissions",
    "insights.api.workbooks.get_workbooks",
    "insights.api.workbooks.import_workbook",
    "insights.api.workbooks.move_item_to_folder",
    "insights.api.workbooks.rename_folder",
    "insights.api.workbooks.toggle_folder_expanded",
    "insights.api.workbooks.update_share_permissions",
    "insights.insights.doctype.insights_chart_v3.insights_chart_v3.InsightsChartv3.duplicate",
    "insights.insights.doctype.insights_chart_v3.insights_chart_v3.InsightsChartv3.export",
    "insights.insights.doctype.insights_chart_v3.insights_chart_v3.InsightsChartv3.update_access",
    "insights.insights.doctype.insights_dashboard.insights_dashboard.InsightsDashboard.clear_charts_cache",
    "insights.insights.doctype.insights_dashboard.insights_dashboard.InsightsDashboard.fetch_chart_data",
    "insights.insights.doctype.insights_dashboard.insights_dashboard.InsightsDashboard.is_private",
    "insights.insights.doctype.insights_dashboard.insights_dashboard.get_dashboard_file",
    "insights.insights.doctype.insights_dashboard.insights_dashboard.get_queries_column",
    "insights.insights.doctype.insights_dashboard.insights_dashboard.get_query_columns",
    "insights.insights.doctype.insights_dashboard_v3.insights_dashboard_v3.InsightsDashboardv3.get_distinct_column_values",
    "insights.insights.doctype.insights_dashboard_v3.insights_dashboard_v3.InsightsDashboardv3.track_view",
    "insights.insights.doctype.insights_dashboard_v3.insights_dashboard_v3.InsightsDashboardv3.update_access",
    "insights.insights.doctype.insights_data_source.insights_data_source.InsightsDataSourceClient.delete_table_link",
    "insights.insights.doctype.insights_data_source.insights_data_source.InsightsDataSourceClient.enqueue_sync_tables",
    "insights.insights.doctype.insights_data_source.insights_data_source.InsightsDataSourceClient.get_queries",
    "insights.insights.doctype.insights_data_source.insights_data_source.InsightsDataSourceClient.get_schema",
    "insights.insights.doctype.insights_data_source.insights_data_source.InsightsDataSourceClient.get_tables",
    "insights.insights.doctype.insights_data_source.insights_data_source.InsightsDataSourceClient.update_table_link",
    "insights.insights.doctype.insights_data_source_v3.ibis.utils.get_code_completions",
    "insights.insights.doctype.insights_data_source_v3.ibis.utils.get_function_description",
    "insights.insights.doctype.insights_data_source_v3.ibis.utils.get_function_list",
    "insights.insights.doctype.insights_data_source_v3.ibis.utils.validate_expression",
    "insights.insights.doctype.insights_data_source_v3.insights_data_source_v3.InsightsDataSourcev3.test_connection",
    "insights.insights.doctype.insights_query.insights_legacy_query.InsightsLegacyQueryClient.add_column",
    "insights.insights.doctype.insights_query.insights_legacy_query.InsightsLegacyQueryClient.add_table",
    "insights.insights.doctype.insights_query.insights_legacy_query.InsightsLegacyQueryClient.fetch_column_values",
    "insights.insights.doctype.insights_query.insights_legacy_query.InsightsLegacyQueryClient.fetch_columns",
    "insights.insights.doctype.insights_query.insights_legacy_query.InsightsLegacyQueryClient.fetch_join_options",
    "insights.insights.doctype.insights_query.insights_legacy_query.InsightsLegacyQueryClient.fetch_tables",
    "insights.insights.doctype.insights_query.insights_legacy_query.InsightsLegacyQueryClient.move_column",
    "insights.insights.doctype.insights_query.insights_legacy_query.InsightsLegacyQueryClient.remove_column",
    "insights.insights.doctype.insights_query.insights_legacy_query.InsightsLegacyQueryClient.remove_table",
    "insights.insights.doctype.insights_query.insights_legacy_query.InsightsLegacyQueryClient.update_column",
    "insights.insights.doctype.insights_query.insights_legacy_query.InsightsLegacyQueryClient.update_filters",
    "insights.insights.doctype.insights_query.insights_legacy_query.InsightsLegacyQueryClient.update_table",
    "insights.insights.doctype.insights_query.insights_query.InsightsQuery.get_tables_columns",
    "insights.insights.doctype.insights_query.insights_query_client.InsightsQueryClient.add_transform",
    "insights.insights.doctype.insights_query.insights_query_client.InsightsQueryClient.convert",
    "insights.insights.doctype.insights_query.insights_query_client.InsightsQueryClient.convert_to_assisted",
    "insights.insights.doctype.insights_query.insights_query_client.InsightsQueryClient.convert_to_native",
    "insights.insights.doctype.insights_query.insights_query_client.InsightsQueryClient.delete_linked_table",
    "insights.insights.doctype.insights_query.insights_query_client.InsightsQueryClient.duplicate",
    "insights.insights.doctype.insights_query.insights_query_client.InsightsQueryClient.fetch_related_tables_columns",
    "insights.insights.doctype.insights_query.insights_query_client.InsightsQueryClient.reset_and_save",
    "insights.insights.doctype.insights_query.insights_query_client.InsightsQueryClient.reset_transforms",
    "insights.insights.doctype.insights_query.insights_query_client.InsightsQueryClient.run",
    "insights.insights.doctype.insights_query.insights_query_client.InsightsQueryClient.save_as_table",
    "insights.insights.doctype.insights_query.insights_query_client.InsightsQueryClient.set_limit",
    "insights.insights.doctype.insights_query.insights_query_client.InsightsQueryClient.set_status",
    "insights.insights.doctype.insights_query.insights_query_client.InsightsQueryClient.store",
    "insights.insights.doctype.insights_query.insights_query_client.InsightsQueryClient.switch_query_type",
    "insights.insights.doctype.insights_query.insights_query_client.InsightsQueryClient.unstore",
    "insights.insights.doctype.insights_query_chart.insights_query_chart.InsightsQueryChart.add_to_dashboard",
    "insights.insights.doctype.insights_query_chart.insights_query_chart.InsightsQueryChart.update_doc",
    "insights.insights.doctype.insights_query_v3.insights_query_v3.InsightsQueryv3.download_results",
    "insights.insights.doctype.insights_query_v3.insights_query_v3.InsightsQueryv3.duplicate",
    "insights.insights.doctype.insights_query_v3.insights_query_v3.InsightsQueryv3.execute",
    "insights.insights.doctype.insights_query_v3.insights_query_v3.InsightsQueryv3.export",
    "insights.insights.doctype.insights_query_v3.insights_query_v3.InsightsQueryv3.format",
    "insights.insights.doctype.insights_query_v3.insights_query_v3.InsightsQueryv3.get_columns_for_selection",
    "insights.insights.doctype.insights_query_v3.insights_query_v3.InsightsQueryv3.get_count",
    "insights.insights.doctype.insights_query_v3.insights_query_v3.InsightsQueryv3.get_distinct_column_values",
    "insights.insights.doctype.insights_settings.insights_settings.InsightsSettings.update_settings",
    "insights.insights.doctype.insights_table.insights_table.InsightsTable.get_preview",
    "insights.insights.doctype.insights_table.insights_table.InsightsTable.sync_table",
    "insights.insights.doctype.insights_table.insights_table.InsightsTable.update_column_type",
    "insights.insights.doctype.insights_table.insights_table.InsightsTable.update_visibility",
    "insights.insights.doctype.insights_table_import_log.insights_table_import_log.InsightsTableImportLog.mark_as_failed",
    "insights.insights.doctype.insights_table_v3.insights_table_v3.InsightsTablev3.get_stats",
    "insights.insights.doctype.insights_team.insights_team_client.InsightsTeamClient.add_team_member",
    "insights.insights.doctype.insights_team.insights_team_client.InsightsTeamClient.add_team_members",
    "insights.insights.doctype.insights_team.insights_team_client.InsightsTeamClient.add_team_resource",
    "insights.insights.doctype.insights_team.insights_team_client.InsightsTeamClient.add_team_resources",
    "insights.insights.doctype.insights_team.insights_team_client.InsightsTeamClient.delete_team",
    "insights.insights.doctype.insights_team.insights_team_client.InsightsTeamClient.get_members_and_resources",
    "insights.insights.doctype.insights_team.insights_team_client.InsightsTeamClient.remove_team_member",
    "insights.insights.doctype.insights_team.insights_team_client.InsightsTeamClient.remove_team_resource",
    "insights.insights.doctype.insights_team.insights_team_client.InsightsTeamClient.search_team_members",
    "insights.insights.doctype.insights_team.insights_team_client.InsightsTeamClient.search_team_resources",
    "insights.insights.doctype.insights_team.insights_team_client.add_new_team",
    "insights.insights.doctype.insights_team.insights_team_client.get_teams",
    "insights.insights.doctype.insights_user_invitation.insights_user_invitation.InsightsUserInvitation.accept_invitation",
    "insights.insights.doctype.insights_workbook.insights_workbook.InsightsWorkbook.duplicate",
    "insights.insights.doctype.insights_workbook.insights_workbook.InsightsWorkbook.export",
    "insights.insights.doctype.insights_workbook.insights_workbook.InsightsWorkbook.get_lineage_graph",
    "insights.insights.doctype.insights_workbook.insights_workbook.InsightsWorkbook.import_chart",
    "insights.insights.doctype.insights_workbook.insights_workbook.InsightsWorkbook.import_query",
    "insights.insights.doctype.insights_workbook.insights_workbook.InsightsWorkbook.track_view",
    "insights.setup.setup_wizard.check_demo_data_exists",
]


def get_endpoints_accepting_get():
    for module in pkgutil.walk_packages(insights.__path__, "insights."):
        name = module.name
        skipped = ("insights.tests.", ".test_", ".patches.", "__main__")
        if not any(part in name for part in skipped):
            importlib.import_module(name)

    return sorted(
        {
            f"{fn.__module__}.{fn.__qualname__}"
            for fn, methods in frappe.allowed_http_methods_for_whitelisted_func.items()
            if fn.__module__.startswith("insights.")
            and not fn.__module__.startswith("insights.tests.")
            and "GET" in methods
        }
    )


class EndpointsAcceptingGetAreListed(UnitTestCase):
    maxDiff = None

    # @feature permissions.get-keeps-no-write
    def test_an_endpoint_accepts_get_only_when_listed(self):
        self.assertEqual(
            get_endpoints_accepting_get(),
            ENDPOINTS_ACCEPTING_GET,
            "Pass methods=['POST'] to a new endpoint's whitelist decorator.",
        )


class GetWritesAreReported(InsightsIntegrationTestCase):
    # @feature permissions.get-keeps-no-write
    def test_an_endpoint_that_commits_under_get_is_reported(self):
        @insights_whitelist()
        def save_title(title: str):
            frappe.db.commit()  # nosemgrep - the write the watch looks for

        save_title(title="Sales")
        with self.assertRaisesRegex(AssertionError, "save_title commits but accepts GET"):
            self.assert_no_get_writes()

    # @feature permissions.get-keeps-no-write
    def test_an_endpoint_that_accepts_only_post_may_commit(self):
        @insights_whitelist(methods=["POST"])
        def save_title(title: str):
            frappe.db.commit()  # nosemgrep - the write the watch looks for

        save_title(title="Sales")
        self.assert_no_get_writes()
