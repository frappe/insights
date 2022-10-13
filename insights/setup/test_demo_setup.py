# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt


import unittest

from .demo import setup, demo_data_exists


class TestDemoSetup(unittest.TestCase):
    def test_demo_setup(self):
        setup()
        self.assertTrue(demo_data_exists())
