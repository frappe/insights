import frappe
import pandas as pd

from insights.insights.doctype.insights_data_source_v3.ibis_utils import cache_results, get_cached_results
from insights.tests.base import InsightsIntegrationTestCase


class TestResultsCache(InsightsIntegrationTestCase):
    # @feature query.result-cache
    def test_a_cached_result_with_infinity_reads_back_as_blanks(self):
        cache_key = frappe.generate_hash()
        result = pd.DataFrame({"rate": [1.5, float("inf"), float("-inf"), float("nan")]})

        cache_results(cache_key, result)

        self.assertEqual(
            get_cached_results(cache_key).to_dict("records"),
            [{"rate": 1.5}, {"rate": None}, {"rate": None}, {"rate": None}],
        )
