from frappe.tests import UnitTestCase

from insights.insights.doctype.insights_chart_v3.chart_drill import aggregate_conditions


class TestAggregateConditions(UnitTestCase):
    def test_a_conditional_aggregate_carries_its_condition(self):
        self.assertEqual(aggregate_conditions("count_if(status == 'Open')"), ["status == 'Open'"])
        self.assertEqual(aggregate_conditions("sum_if(status == 'Open', amount)"), ["status == 'Open'"])

    def test_a_condition_holding_a_comma_is_read_whole(self):
        self.assertEqual(
            aggregate_conditions("count_if(is_not_in(status, 'a', 'b'), name)"),
            ["is_not_in(status, 'a', 'b')"],
        )

    def test_the_gate_is_read_by_position_and_by_keyword(self):
        self.assertEqual(aggregate_conditions("sum(amount, status == 'Active')"), ["status == 'Active'"])
        self.assertEqual(
            aggregate_conditions("sum(amount, where=status == 'Active')"), ["status == 'Active'"]
        )

    def test_a_one_if_over_the_column_is_a_gate_too(self):
        self.assertEqual(
            aggregate_conditions("sum(one_if(a == 1), where=b == 2)"),
            ["b == 2", "a == 1"],
        )

    def test_a_window_aggregate_pins_nothing(self):
        self.assertEqual(aggregate_conditions("sum(amount, where=a == 1, group_by=b)"), [])
        self.assertEqual(aggregate_conditions("sum(amount, where=a == 1, order_by=b)"), ["a == 1"])

    def test_an_escaped_quote_does_not_end_the_string(self):
        self.assertEqual(aggregate_conditions("count_if(name == 'O\\'Brien')"), ['name == "O\'Brien"'])

    def test_an_ungated_or_unparsable_measure_pins_nothing(self):
        self.assertEqual(aggregate_conditions("sum(amount)"), [])
        self.assertEqual(aggregate_conditions("count_if("), [])
        self.assertEqual(aggregate_conditions(""), [])
