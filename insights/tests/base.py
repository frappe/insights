import inspect
import sys
from contextlib import ExitStack
from unittest.mock import patch

import frappe
from frappe.database.database import Database
from frappe.tests import IntegrationTestCase
from frappe.utils import background_jobs

from insights.insights.doctype.insights_data_source_v3 import data_warehouse
from insights.insights.doctype.insights_data_source_v3.connectors import duckdb
from insights.tests.factories import as_user, is_visible


def get_whitelisted_caller():
    """The innermost whitelisted function on the call stack.

    Innermost, because `run_doc_method` accepts GET and Frappe checks the
    document method it dispatches to on its own.
    """
    functions = {inspect.unwrap(fn).__code__: fn for fn in frappe.whitelisted}
    frame = sys._getframe(2)
    while frame:
        if fn := functions.get(frame.f_code):
            return fn
        frame = frame.f_back


def watch_get_writes(writes: list[str]) -> ExitStack:
    """Record every write that a GET request would keep.

    Frappe rolls back the database after a GET request, and drops the jobs
    enqueued after commit with it. So a cross-site link to an endpoint changes
    nothing unless the endpoint commits, enqueues a job that does not wait for
    the commit, or writes to DuckDB. Such an endpoint must accept only POST.
    """

    def record(write):
        fn = get_whitelisted_caller()
        if (
            fn
            and fn.__module__.startswith("insights.")
            and "GET" in frappe.allowed_http_methods_for_whitelisted_func[fn]
        ):
            writes.append(f"{fn.__module__}.{fn.__qualname__} {write} but accepts GET")

    def watch(owner, name, write, is_write=lambda *args, **kwargs: True):
        original = getattr(owner, name)

        def watcher(*args, **kwargs):
            if is_write(*args, **kwargs):
                record(write)
            return original(*args, **kwargs)

        return patch.object(owner, name, watcher)

    def opens_for_write(path, read_only=True, *args, **kwargs):
        return not read_only

    def runs_without_commit(*args, enqueue_after_commit=False, **kwargs):
        return not enqueue_after_commit

    stack = ExitStack()
    stack.enter_context(watch(Database, "commit", "commits"))
    stack.enter_context(watch(background_jobs, "enqueue", "enqueues a job", runs_without_commit))
    stack.enter_context(watch(frappe, "enqueue", "enqueues a job", runs_without_commit))
    for module in (duckdb, data_warehouse):
        stack.enter_context(watch(module, "open_local_duckdb", "writes to DuckDB", opens_for_write))
    return stack


class InsightsIntegrationTestCase(IntegrationTestCase):
    SAVEPOINT = None
    COMMIT_AFTER_CLASS_SETUP = True
    COMMIT_AFTER_CLASS_TEARDOWN = True
    COMMIT_AFTER_TEST_SETUP = False
    COMMIT_AFTER_TEST_TEARDOWN = False

    @classmethod
    def before_class(cls):
        pass

    @classmethod
    def after_class(cls):
        pass

    def before_test(self):
        pass

    def after_test(self):
        pass

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.get_writes = []
        cls.addClassCleanup(watch_get_writes(cls.get_writes).close)
        with as_user("Administrator"):
            cls.before_class()
            if cls.COMMIT_AFTER_CLASS_SETUP:
                frappe.db.commit()
        cls.assert_no_get_writes()

    @classmethod
    def assert_no_get_writes(cls):
        writes, cls.get_writes[:] = list(dict.fromkeys(cls.get_writes)), []
        if writes:
            raise AssertionError("Pass methods=['POST'] to their whitelist decorator:\n" + "\n".join(writes))

    @classmethod
    def tearDownClass(cls):
        try:
            with as_user("Administrator"):
                cls.after_class()
                if cls.COMMIT_AFTER_CLASS_TEARDOWN:
                    frappe.db.commit()
        finally:
            super().tearDownClass()

    def setUp(self):
        super().setUp()
        self.original_user = frappe.session.user
        self.addCleanup(frappe.set_user, self.original_user)
        frappe.set_user("Administrator")
        self.addCleanup(self.assert_no_get_writes)
        self.before_test()
        if self.SAVEPOINT:
            frappe.db.savepoint(self.SAVEPOINT)
        elif self.COMMIT_AFTER_TEST_SETUP:
            frappe.db.commit()

    def tearDown(self):
        try:
            frappe.set_user("Administrator")
            if self.SAVEPOINT:
                frappe.db.rollback(save_point=self.SAVEPOINT)
            self.after_test()
            if self.COMMIT_AFTER_TEST_TEARDOWN and not self.SAVEPOINT:
                frappe.db.commit()
        finally:
            super().tearDown()

    def as_user(self, user):
        return as_user(user)

    def set_team_permissions(self, enabled):
        """Turn `enable_permissions` on or off for one test.

        The setting scopes data sources and tables to teams. It has never scoped
        a workbook's contents, so a rule over those has to hold either way. The
        allowed-resource lookup is site-cached, so the cache goes with it.
        """
        from insights.insights.doctype.insights_team.insights_team import clear_cache

        original = frappe.db.get_single_value("Insights Settings", "enable_permissions")
        frappe.db.set_single_value("Insights Settings", "enable_permissions", enabled)
        clear_cache()
        self.addCleanup(clear_cache)
        self.addCleanup(frappe.db.set_single_value, "Insights Settings", "enable_permissions", original)

    def assert_visible_to(self, user, doctype, name, message=None):
        with self.as_user(user):
            self.assertTrue(
                is_visible(doctype, name),
                message or f"{doctype} {name} should be visible to {user}",
            )

    def assert_not_visible_to(self, user, doctype, name, message=None):
        with self.as_user(user):
            self.assertFalse(
                is_visible(doctype, name),
                message or f"{doctype} {name} should not be visible to {user}",
            )
