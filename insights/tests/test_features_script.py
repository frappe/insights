"""What `insights/tests/features.py` reads off the suite, and when `check` fails.

The generator is the only reader of the `@feature` directive, so what it counts
as a test and as a directive is the contract every annotated test is written
against.
"""

import tempfile
import unittest
from pathlib import Path

from insights.tests import features

FEATURES_MD = """# Features

## query

| Slug | Feature | Coverage |
|---|---|---|
| query.filter | A user adds a filter. | none |
| query.join | A user joins a second table. | none |
"""

BACKEND_PY = """import unittest


class TestQuery(unittest.TestCase):
    # @feature query.filter query.join
    def test_a_filter_cuts_the_rows(self):
        pass

    def test_nothing_names_a_feature(self):
        pass
"""

UNIT_TS = """describe('filter', () => {
\t// @feature query.filter
\tit('keeps the rows the filter names', () => {})
})
"""

E2E_TS = """test.describe('query', () => {
\t// @feature query.join\t
\ttest(
\t\t'a user joins a second table',
\t\tasync ({ page }) => {},
\t)
})
"""

UNKNOWN_TS = """// @feature query.sorcery
it('sorts by a slug nobody declared', () => {})
"""


def write_tree(root, files):
    for relative, text in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)


class TestFeaturesScript(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.features = self.root / "features.md"
        self.features.write_text(FEATURES_MD)
        self.output = self.root / "coverage.md"

    def build(self, files):
        write_tree(self.root, files)
        return features.generate(self.features, self.root)

    def run_cli(self, command):
        return features.main(
            [
                command,
                "--features",
                str(self.features),
                "--output",
                str(self.output),
                "--root",
                str(self.root),
            ]
        )

    # @feature tooling.feature-coverage
    def test_a_directive_lands_on_every_slug_it_names(self):
        coverage, _, _, _ = self.build({"insights/tests/test_query.py": BACKEND_PY})
        label = "insights/tests/test_query.py::test_a_filter_cuts_the_rows"
        self.assertIn(f"| query.filter | A user adds a filter. | {label} |", coverage)
        self.assertIn(f"| query.join | A user joins a second table. | {label} |", coverage)

    # @feature tooling.feature-coverage
    def test_a_test_without_a_directive_is_listed(self):
        coverage, _, undirected, _ = self.build({"insights/tests/test_query.py": BACKEND_PY})
        self.assertEqual([test.name for test in undirected], ["test_nothing_names_a_feature"])
        self.assertIn("insights/tests/test_query.py:9 — test_nothing_names_a_feature", coverage)

    # @feature tooling.feature-coverage
    def test_a_vitest_case_is_cited_by_its_title(self):
        coverage, _, _, _ = self.build({"frontend/src2/query/filter.test.ts": UNIT_TS})
        self.assertIn('frontend/src2/query/filter.test.ts::"keeps the rows the filter names"', coverage)

    # @feature tooling.feature-coverage
    def test_an_e2e_title_on_the_next_line_is_read(self):
        coverage, _, _, _ = self.build({"frontend/e2e/tests/query.spec.ts": E2E_TS})
        self.assertIn(
            '| query.join | A user joins a second table. |  |  | "a user joins a second table" |', coverage
        )

    # @feature tooling.feature-coverage
    def test_a_slug_no_feature_declares_is_reported(self):
        coverage, unknown, _, _ = self.build({"frontend/src2/query/sort.test.ts": UNKNOWN_TS})
        self.assertEqual([slug for slug, _ in unknown], ["query.sorcery"])
        self.assertIn("- `query.sorcery` — frontend/src2/query/sort.test.ts:2", coverage)

    # @feature tooling.feature-coverage
    def test_check_fails_until_the_generated_file_is_written(self):
        write_tree(self.root, {"frontend/src2/query/filter.test.ts": UNIT_TS})
        self.assertEqual(self.run_cli("check"), 1)
        self.assertEqual(self.run_cli("generate"), 0)
        self.assertEqual(self.run_cli("check"), 0)

    # @feature tooling.feature-coverage
    def test_check_fails_on_a_test_without_a_directive(self):
        write_tree(self.root, {"insights/tests/test_query.py": BACKEND_PY})
        self.run_cli("generate")
        self.assertEqual(self.run_cli("check"), 1)
