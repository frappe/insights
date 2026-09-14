# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt


import unittest

from .demo import DemoDataFactory


class TestDemoSetup(unittest.TestCase):
    # @feature settings.demo-data
    def test_import_demo_data(self):
        factory = DemoDataFactory().run()
        self.assertTrue(factory.demo_data_exists())
