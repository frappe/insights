import importlib
import runpy
from unittest.mock import patch

import insights.desk
from insights.tests.base import InsightsIntegrationTestCase


class TestWithoutDeskIslands(InsightsIntegrationTestCase):
    # @feature desk.without-islands
    def test_insights_stays_out_of_desk_on_a_frappe_without_islands(self):
        self.assertTrue(desk_hooks(runpy.run_module("insights.hooks")))

        self.addCleanup(importlib.reload, insights.desk)
        with patch("insights.find_spec", return_value=None):
            hooks = runpy.run_module("insights.hooks")
            importlib.reload(insights.desk)

        self.assertEqual(desk_hooks(hooks), [])
        self.assertEqual(insights.desk.DESK_ISLANDS, {})
        self.assertFalse(insights.desk.can_show_charts_in_desk())
        self.assertIsNone(insights.desk.get_form_chart("any chart"))
        self.assertEqual(insights.desk.claims_on("Insights Chart v3", {}), [])
        self.assertEqual(insights.desk.dangling_claims(), [])
        with patch.object(insights.desk, "create_custom_fields") as create_custom_fields:
            insights.desk.install_custom_fields()
        create_custom_fields.assert_called_once_with({})


def desk_hooks(hooks: dict) -> list[str]:
    """Every hook value that names Insights' desk code, so a desk hook added
    later outside the `desk_islands()` block is caught too."""

    def values(value):
        if isinstance(value, str):
            yield value
        elif isinstance(value, dict):
            for item in value.values():
                yield from values(item)
        elif isinstance(value, list | tuple):
            for item in value:
                yield from values(item)

    return [
        value
        for name, hook in hooks.items()
        if not name.startswith("_")
        for value in values(hook)
        if "insights.desk." in value or "desk_chart_form.js" in value
    ]
