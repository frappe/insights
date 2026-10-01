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
    "insights.api.ai.lineage.describe_query",
    "insights.api.ai.search.search_columns",
    "insights.api.ai.search.search_content",
    "insights.api.alerts.get_alerts",
    "insights.api.authoring.download_chart_rows",
    "insights.api.authoring.download_drill_rows",
    "insights.api.authoring.get_chart_count",
    "insights.api.authoring.get_chart_data",
    "insights.api.authoring.get_drill_data",
    "insights.api.authoring.get_drill_dimensions",
    "insights.api.authoring.get_drill_rows_range",
    "insights.api.authoring.get_drill_rows_values",
    "insights.api.dashboards.get_dashboards",
    "insights.api.data_sources.create_data_source",
    "insights.api.data_sources.get_all_data_sources",
    "insights.api.data_sources.get_data_source_table",
    "insights.api.data_sources.get_data_source_table_columns",
    "insights.api.data_sources.get_data_source_table_row_count",
    "insights.api.data_sources.get_data_source_tables",
    "insights.api.data_sources.get_data_sources_of_tables",
    "insights.api.data_sources.get_schema",
    "insights.api.data_sources.get_table_links",
    "insights.api.data_sources.test_connection",
    "insights.api.data_sources.update_table_links",
    "insights.api.data_store.get_data_store_tables",
    "insights.api.get_app_version",
    "insights.api.get_doc",
    "insights.api.get_file_data",
    "insights.api.get_security_update",
    "insights.api.get_site_info",
    "insights.api.get_user_info",
    "insights.api.maps.find_unresolved_regions",
    "insights.api.maps.get_available_regions",
    "insights.api.maps.save_region_mappings",
    "insights.api.run_doc_method",
    "insights.api.search.search_workbook_items",
    "insights.api.translations.get_translations",
    "insights.api.user.accept_invitation",
    "insights.api.user.add_insights_user",
    "insights.api.user.create_team",
    "insights.api.user.delete_team",
    "insights.api.user.get_roles",
    "insights.api.user.get_teams",
    "insights.api.user.get_users",
    "insights.api.user.update_team",
    "insights.api.user.update_user",
    "insights.api.view.download_chart_rows",
    "insights.api.view.download_drill_rows",
    "insights.api.view.get_card_range",
    "insights.api.view.get_card_values",
    "insights.api.view.get_chart",
    "insights.api.view.get_chart_count",
    "insights.api.view.get_chart_data",
    "insights.api.view.get_dashboard",
    "insights.api.view.get_drill_data",
    "insights.api.view.get_drill_rows_range",
    "insights.api.view.get_drill_rows_values",
    "insights.api.view.get_filter_range",
    "insights.api.view.get_filter_values",
    "insights.api.workbooks.create_folder",
    "insights.api.workbooks.delete_folder",
    "insights.api.workbooks.get_export_modules",
    "insights.api.workbooks.get_share_permissions",
    "insights.api.workbooks.get_workbooks",
    "insights.api.workbooks.import_workbook",
    "insights.api.workbooks.is_workbook_file",
    "insights.api.workbooks.move_item_to_folder",
    "insights.api.workbooks.rename_folder",
    "insights.api.workbooks.toggle_folder_expanded",
    "insights.api.workbooks.update_share_permissions",
    "insights.insights.doctype.insights_chart_v3.insights_chart_v3.InsightsChartv3.duplicate",
    "insights.insights.doctype.insights_chart_v3.insights_chart_v3.InsightsChartv3.export",
    "insights.insights.doctype.insights_chart_v3.insights_chart_v3.InsightsChartv3.published_reach",
    "insights.insights.doctype.insights_dashboard_v3.insights_dashboard_v3.InsightsDashboardv3.get_distinct_column_values",
    "insights.insights.doctype.insights_dashboard_v3.insights_dashboard_v3.InsightsDashboardv3.get_filter_column_range",
    "insights.insights.doctype.insights_dashboard_v3.insights_dashboard_v3.InsightsDashboardv3.track_view",
    "insights.insights.doctype.insights_dashboard_v3.insights_dashboard_v3.InsightsDashboardv3.update_access",
    "insights.insights.doctype.insights_data_source_v3.ibis.utils.get_code_completions",
    "insights.insights.doctype.insights_data_source_v3.ibis.utils.get_function_description",
    "insights.insights.doctype.insights_data_source_v3.ibis.utils.get_function_list",
    "insights.insights.doctype.insights_data_source_v3.ibis.utils.validate_expression",
    "insights.insights.doctype.insights_data_source_v3.insights_data_source_v3.InsightsDataSourcev3.test_connection",
    "insights.insights.doctype.insights_query_v3.insights_query_v3.InsightsQueryv3.download_results",
    "insights.insights.doctype.insights_query_v3.insights_query_v3.InsightsQueryv3.duplicate",
    "insights.insights.doctype.insights_query_v3.insights_query_v3.InsightsQueryv3.execute",
    "insights.insights.doctype.insights_query_v3.insights_query_v3.InsightsQueryv3.export",
    "insights.insights.doctype.insights_query_v3.insights_query_v3.InsightsQueryv3.format",
    "insights.insights.doctype.insights_query_v3.insights_query_v3.InsightsQueryv3.get_column_range",
    "insights.insights.doctype.insights_query_v3.insights_query_v3.InsightsQueryv3.get_columns_for_selection",
    "insights.insights.doctype.insights_query_v3.insights_query_v3.InsightsQueryv3.get_count",
    "insights.insights.doctype.insights_query_v3.insights_query_v3.InsightsQueryv3.get_distinct_column_values",
    "insights.insights.doctype.insights_query_v3.insights_query_v3.InsightsQueryv3.profile_column",
    "insights.insights.doctype.insights_settings.insights_settings.InsightsSettings.update_settings",
    "insights.insights.doctype.insights_table_import_log.insights_table_import_log.InsightsTableImportLog.mark_as_failed",
    "insights.insights.doctype.insights_table_v3.insights_table_v3.InsightsTablev3.get_stats",
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
        if not name.startswith("insights.tests.") and ".test_" not in name and not name.endswith("__main__"):
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
