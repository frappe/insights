# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""The demo dataset: a declarative spec in `spec.py`, an engine in `generator.py`.

Tests and CI generate the dataset instead of reading a committed binary. A
binary hides a broken join. A spec shows it in the diff.
"""

from insights.setup.demo_data.generator import (
    BrokenFixture,
    check_integrity,
    generate,
)
from insights.setup.demo_data.spec import DEMO_SPEC

__all__ = [
    "DEMO_SPEC",
    "BrokenFixture",
    "check_integrity",
    "generate",
]
