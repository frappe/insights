# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest
from unittest.mock import MagicMock, patch

import frappe
import pandas as pd

from insights.insights.doctype.insights_data_source_v3.ibis_utils import (
    DEFAULT_MAX_CONCURRENT_QUERIES,
    LOCK_TIMEOUT,
    QUERY_LOCK_PREFIX,
    cache_results,
    execute_with_lock,
    get_cached_results,
    get_max_concurrent_queries,
    get_pending_query_result,
    has_cached_results,
    is_query_executing,
    release_lock,
    release_semaphore,
    try_acquire_lock,
    try_acquire_semaphore,
)


class TestQueryLocking(unittest.TestCase):
    def setUp(self):
        self.test_cache_key = f"test_lock_{frappe.generate_hash(length=8)}"
        self.lock_key = self.test_cache_key
        self.cleanup_test_keys()

    def tearDown(self):
        self.cleanup_test_keys()

    def cleanup_test_keys(self):
        try:
            cache = frappe.cache()
            cache.delete(cache.make_key(self.lock_key))
            results_key = "insights:query_results:" + self.test_cache_key
            cache.delete(cache.make_key(results_key))
        except Exception:
            pass

    def test_acquire_lock_success(self):
        acquired = try_acquire_lock(self.lock_key)
        self.assertTrue(acquired, "Should acquire lock when not held")
        release_lock(self.lock_key)

    def test_acquire_lock_fails_when_held(self):
        first_acquired = try_acquire_lock(self.lock_key)
        self.assertTrue(first_acquired, "First acquisition should succeed")

        second_acquired = try_acquire_lock(self.lock_key)
        self.assertFalse(second_acquired, "Second acquisition should fail")

        release_lock(self.lock_key)

    def test_release_lock(self):
        try_acquire_lock(self.lock_key)
        release_lock(self.lock_key)

        acquired = try_acquire_lock(self.lock_key)
        self.assertTrue(acquired, "Should acquire lock after release")
        release_lock(self.lock_key)

    def test_is_query_executing(self):
        self.assertFalse(is_query_executing(self.test_cache_key), "Should not be executing initially")

        acquired = try_acquire_lock(self.lock_key)
        self.assertTrue(acquired, "Lock should be acquired")

        # is_query_executing checks the raw key, but lock uses prefixed key
        # so this checks the cache_key without prefix — matches how it's used in get_pending_query_result
        executing = is_query_executing(self.lock_key)
        self.assertTrue(executing, "Should be executing after lock acquired")

        release_lock(self.lock_key)

        self.assertFalse(is_query_executing(self.lock_key), "Should not be executing after lock released")

    def test_semaphore_acquire_success(self):
        slot = try_acquire_semaphore()
        self.assertIsNotNone(slot, "Should acquire semaphore slot")
        release_semaphore()

    def test_semaphore_limit(self):
        max_queries = get_max_concurrent_queries()
        acquired_slots = []

        for _i in range(max_queries):
            slot = try_acquire_semaphore()
            if slot is not None:
                acquired_slots.append(slot)
        extra_slot = try_acquire_semaphore()
        self.assertIsNone(extra_slot, f"Should not acquire more than {max_queries} slots")

        for _ in acquired_slots:
            release_semaphore()

    def test_semaphore_release(self):
        max_queries = get_max_concurrent_queries()

        for _ in range(max_queries):
            try_acquire_semaphore()

        self.assertIsNone(try_acquire_semaphore())

        release_semaphore()
        slot = try_acquire_semaphore()
        self.assertIsNotNone(slot, "Should acquire after release")

        for _ in range(max_queries):
            release_semaphore()

    def test_cache_results(self):
        test_data = pd.DataFrame({"col1": [1, 2, 3], "col2": ["a", "b", "c"]})

        cache_results(self.test_cache_key, test_data, cache_expiry=60)

        self.assertTrue(has_cached_results(self.test_cache_key), "Should have cached results")

        cached = get_cached_results(self.test_cache_key)
        self.assertIsNotNone(cached, "Should retrieve cached results")
        self.assertEqual(len(cached), 3, "Should have 3 rows")

    def test_cache_miss(self):
        non_existent_key = f"non_existent_{frappe.generate_hash(length=8)}"

        self.assertFalse(
            has_cached_results(non_existent_key), "Should not have cached results for non-existent key"
        )

        self.assertIsNone(get_cached_results(non_existent_key), "Should return None for cache miss")

    def test_pending_query_result_executing(self):
        acquired = try_acquire_lock(self.lock_key)
        self.assertTrue(acquired, "Should acquire lock for test")

        # get_pending_query_result checks is_query_executing with the raw cache_key
        # but the lock is on lock_key (with prefix), so this tests the actual flow
        result = get_pending_query_result(self.lock_key)
        self.assertEqual(result["status"], "pending", "Should return pending status")

        release_lock(self.lock_key)

    def test_pending_query_result_completed(self):
        test_data = pd.DataFrame({"value": [717]})
        cache_results(self.test_cache_key, test_data, cache_expiry=60)

        result = get_pending_query_result(self.test_cache_key)
        self.assertEqual(result["status"], "completed", "Should return completed status")
        self.assertIsNotNone(result["result"], "Should have result data")

    def test_pending_query_result_not_found(self):
        non_existent_key = f"non_existent_{frappe.generate_hash(length=8)}"

        result = get_pending_query_result(non_existent_key)
        self.assertEqual(result["status"], "not_found", "Should return not_found status")

    def test_execute_with_lock_returns_pending_when_locked(self):
        try_acquire_lock(self.lock_key)

        mock_query = MagicMock()

        result, time_taken = execute_with_lock(
            mock_query,
            "SELECT 1",
            self.test_cache_key,
            cache=True,
            cache_expiry=60,
            force=False,
            reference_name="test",
        )

        self.assertIsInstance(result, dict, "Should return dict")
        self.assertEqual(result["status"], "pending", "Should return pending status")
        self.assertEqual(result["cache_key"], self.test_cache_key)

        release_lock(self.lock_key)

    def test_execute_with_lock_releases_lock_on_completion(self):
        mock_query = MagicMock()
        mock_query.execute.return_value = pd.DataFrame({"result": [1]})

        with patch("insights.insights.doctype.insights_data_source_v3.ibis_utils.create_execution_log"):
            execute_with_lock(
                mock_query,
                "SELECT 1",
                self.test_cache_key,
                cache=True,
                cache_expiry=60,
                force=False,
                reference_name="test",
            )

        self.assertFalse(
            is_query_executing(self.test_cache_key),
            "Lock should be released after execution",
        )

    def test_execute_with_lock_releases_lock_on_error(self):
        mock_query = MagicMock()
        mock_query.execute.side_effect = Exception("Test error")

        with self.assertRaises(Exception):
            with patch("insights.insights.doctype.insights_data_source_v3.ibis_utils.create_execution_log"):
                execute_with_lock(
                    mock_query,
                    "SELECT 1",
                    self.test_cache_key,
                    cache=True,
                    cache_expiry=60,
                    force=False,
                    reference_name="test",
                )

        self.assertFalse(
            is_query_executing(self.test_cache_key),
            "Lock should be released even after error",
        )

    def test_coalescing_flow(self):
        first_acquired = try_acquire_lock(self.lock_key)
        self.assertTrue(first_acquired, "First request should acquire lock")

        self.assertTrue(is_query_executing(self.lock_key), "Query should be marked as executing")

        result = get_pending_query_result(self.lock_key)
        self.assertEqual(result["status"], "pending", "Second request should get pending")

        test_data = pd.DataFrame({"value": [717]})
        cache_results(self.test_cache_key, test_data, cache_expiry=60)
        release_lock(self.lock_key)

        result = get_pending_query_result(self.test_cache_key)
        self.assertEqual(result["status"], "completed", "Should get completed after cache")
        self.assertEqual(len(result["result"]), 1)
        self.assertEqual(result["result"]["value"].iloc[0], 717)

    def test_redis_failure_fails_open(self):
        original_cache = frappe.cache

        def mock_cache():
            mock = MagicMock()
            mock.set.side_effect = Exception("Redis connection failed")
            return mock

        try:
            frappe.cache = mock_cache
            acquired = try_acquire_lock("test_lock_failure")
            self.assertTrue(acquired, "Should fail open and allow execution")
        finally:
            frappe.cache = original_cache


class TestQueryLockingConstants(unittest.TestCase):
    def test_lock_timeout_reasonable(self):
        self.assertGreaterEqual(LOCK_TIMEOUT, 60, "Lock timeout should be at least 60 seconds")
        self.assertLessEqual(LOCK_TIMEOUT, 600, "Lock timeout should be at most 10 minutes")

    def test_default_max_concurrent_queries_reasonable(self):
        self.assertGreaterEqual(DEFAULT_MAX_CONCURRENT_QUERIES, 1)
        self.assertLessEqual(DEFAULT_MAX_CONCURRENT_QUERIES, 18)

    def test_lock_prefix_namespaced(self):
        self.assertTrue(
            QUERY_LOCK_PREFIX.startswith("insights"), "Lock prefix should be namespaced to insights"
        )


if __name__ == "__main__":
    unittest.main()
