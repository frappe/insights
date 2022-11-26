# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

INCLUSIONS = ["*.py"]

EXCLUSIONS = [
    "*.js",
    "*.xml",
    "*.pyc",
    "*.css",
    "*.less",
    "*.scss",
    "*.vue",
    "*.html",
    "*/test_*",
    "*/node_modules/*",
    "*/patches/*",
    "*/config/*",
    "*/tests/*",
    "*/insights/setup.py",
    "*/coverage.py",
    "*/patches/*",
]


class CodeCoverage:
    def __init__(self, with_coverage, app):
        self.with_coverage = with_coverage
        self.app = app or "insights"

    def __enter__(self):
        if self.with_coverage:
            import os

            from coverage import Coverage
            from frappe.utils import get_bench_path

            # Generate coverage report only for app that is being tested
            source_path = os.path.join(get_bench_path(), "apps", self.app)

            self.coverage = Coverage(
                source=[source_path], omit=EXCLUSIONS, include=INCLUSIONS
            )
            self.coverage.start()

    def __exit__(self, exc_type, exc_value, traceback):
        if self.with_coverage:
            self.coverage.stop()
            self.coverage.save()
            self.coverage.xml_report()
            print("Saved Coverage")
