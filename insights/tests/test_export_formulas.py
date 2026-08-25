"""An exported cell is data, not a program.

A query reads columns other people write. A value beginning with `=` or `@` is a
live formula once a spreadsheet opens the file, and a formula can reach DDE or a
shell on the machine of whoever exported. The export is the last place that can
say the value is text.

`+` and `-` open a formula too, and they also start ordinary data. Quoting every
one of them would put a stray apostrophe into phone numbers and text-column
negatives, and a CSV is read by scripts as often as by people. A signed value is
quoted only when it carries the characters a formula needs to call something.
"""

import base64
from io import BytesIO
from unittest.mock import MagicMock, patch
from zipfile import ZipFile

import frappe
import pandas as pd
from frappe.tests import UnitTestCase

from insights.tests.base import InsightsIntegrationTestCase
from insights.tests.factories import DT, create_test_query, create_test_workbook, delete_users
from insights.tests.permissions_utils import ADMIN, create_test_users
from insights.utils import as_text

PAYLOAD = "=cmd|'/c calc'!A1"


def exported(**columns):
    return as_text(pd.DataFrame(columns))


def sheet_xml(df):
    output = BytesIO()
    df.to_excel(output, index=False, engine="openpyxl")
    with ZipFile(BytesIO(output.getvalue())) as workbook:
        return workbook.read("xl/worksheets/sheet1.xml").decode()


class TestFormulasAreNeutralised(UnitTestCase):
    def frame(self):
        return pd.DataFrame({"name": [PAYLOAD, "Ada Lovelace"], "amount": [1, 2]})

    def test_a_formula_is_quoted_in_csv(self):
        self.assertIn(f"'{PAYLOAD}", as_text(self.frame()).to_csv(index=False))

    def test_a_formula_does_not_become_a_formula_cell_in_excel(self):
        self.assertNotIn("<f>", sheet_xml(as_text(self.frame())))

    def test_the_triggers_that_always_open_a_formula(self):
        triggers = ("=SUM(A1)", "@SUM(A1)", "\tone", "\rone", "\none")
        self.assertEqual(
            list(exported(value=list(triggers))["value"]),
            [f"'{value}" for value in triggers],
        )

    def test_a_signed_value_that_can_call_something_is_quoted(self):
        payloads = ("+cmd|'/c calc'!A1", "-2+3+cmd|'/c calc'!A0", "-SUM(A1:A2)")
        self.assertEqual(
            list(exported(value=list(payloads))["value"]),
            [f"'{value}" for value in payloads],
        )


class TestOrdinaryDataSurvives(UnitTestCase):
    """The cost of the rule, pinned so it cannot grow."""

    def test_a_phone_number_keeps_its_plus(self):
        self.assertEqual(exported(phone=["+91 9876543210"])["phone"][0], "+91 9876543210")

    def test_a_negative_held_as_text_is_untouched(self):
        values = ["-5", "-1234.50", "-0.5"]
        self.assertEqual(list(exported(value=values)["value"]), values)

    def test_numbers_are_untouched(self):
        self.assertEqual(exported(amount=[-5, 12])["amount"][0], -5)

    def test_headers_are_not_rewritten(self):
        """They name the columns of whatever reads the file next."""
        self.assertEqual(list(exported(**{PAYLOAD: ["value"]}).columns), [PAYLOAD])

    def test_ordinary_text_is_untouched(self):
        self.assertEqual(exported(name=["Ada Lovelace"])["name"][0], "Ada Lovelace")


class TestQueryExportAppliesTheRule(InsightsIntegrationTestCase):
    """The rule is worth nothing if the download path skips it."""

    @classmethod
    def before_class(cls):
        create_test_users()
        cls.workbook = create_test_workbook(ADMIN, title="Export Workbook").name
        cls.query = create_test_query(ADMIN, cls.workbook, title="Export Query").name

    @classmethod
    def after_class(cls):
        frappe.delete_doc(DT.WORKBOOK, cls.workbook, force=True, ignore_permissions=True)
        delete_users(ADMIN)

    def download(self, format):
        doc = frappe.get_doc(DT.QUERY, self.query)
        rows = pd.DataFrame({"name": [PAYLOAD]})
        built = MagicMock()
        built.columns = []
        built.limit.return_value = built
        with (
            patch.object(type(doc), "build", return_value=built),
            patch(
                "insights.insights.doctype.insights_query_v3.insights_query_v3.execute_ibis_query",
                return_value=(rows, 0),
            ),
        ):
            return doc.download_results(format=format)

    def test_the_csv_download_quotes_a_formula(self):
        self.assertIn(f"'{PAYLOAD}", self.download("csv"))

    def test_the_excel_download_writes_no_formula_cell(self):
        workbook = base64.b64decode(self.download("excel"))
        with ZipFile(BytesIO(workbook)) as sheet:
            self.assertNotIn("<f>", sheet.read("xl/worksheets/sheet1.xml").decode())
