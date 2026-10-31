# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import threading
import time
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from insights.exceptions import QueryCancelled, QueryTimeout
from insights.resources import ResourcePool, single_flight


class TestResourcePool(IntegrationTestCase):
    def pool(self, capacity, **kwargs):
        name = f"test:{frappe.generate_hash(length=10)}"
        pool = ResourcePool(name, capacity, **kwargs)
        self.addCleanup(frappe.cache.delete, *(frappe.cache.make_key(key, shared=True) for key in pool.keys))
        return pool

    def as_holder(self, user=None, site=None):
        """Acquire as another user or site, as another request would."""
        site_patch = patch.object(frappe.local, "site", site or frappe.local.site)
        session_patch = patch.object(frappe.local, "session", frappe._dict(user=user or frappe.session.user))
        return site_patch, session_patch

    def acquire_as(self, pool, user=None, site=None, wait=0):
        site_patch, session_patch = self.as_holder(user, site)
        with site_patch, session_patch:
            return pool.acquire(wait=wait)

    # @feature data-store.slot-pool
    def test_a_slot_a_killed_worker_held_comes_back_when_its_lease_ends(self):
        pool = self.pool(1, lease_seconds=0.3)
        self.assertTrue(pool.acquire())  # never released, as by a worker that was killed

        self.assertIsNone(pool.acquire())
        time.sleep(0.4)
        self.assertTrue(pool.acquire())

    # @feature data-store.slot-pool
    def test_a_lower_capacity_applies_to_the_next_request_while_slots_are_held(self):
        pool = self.pool(3)
        held = [self.acquire_as(pool, user=f"u{i}@example.com") for i in range(2)]
        self.assertTrue(all(held))

        smaller = ResourcePool(pool.name, 2)
        self.assertIsNone(self.acquire_as(smaller, user="u3@example.com"))

        pool.release(held[0])
        self.assertTrue(self.acquire_as(smaller, user="u3@example.com"))

    # @feature data-store.slot-pool
    def test_requests_that_arrive_together_on_a_new_pool_take_only_its_capacity(self):
        pool = self.pool(3)
        site = frappe.local.site
        start = threading.Barrier(12)
        taken = []

        def request(i):
            frappe.local.site = site
            frappe.local.session = frappe._dict(user=f"u{i}@example.com")
            start.wait()
            taken.append(pool.acquire())

        threads = [threading.Thread(target=request, args=(i,)) for i in range(12)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(sum(1 for lease in taken if lease), 3)
        self.assertEqual(len(pool.holders()), 3)

    # @feature data-store.slot-pool
    def test_one_user_holds_at_most_their_share_while_another_user_reads(self):
        pool = self.pool(4, per_user=2)
        alone = [self.acquire_as(pool, user="api@example.com") for _ in range(4)]
        self.assertTrue(all(alone))
        for lease in alone[2:]:
            pool.release(lease)

        self.assertTrue(self.acquire_as(pool, user="reader@example.com"))
        self.assertIsNone(self.acquire_as(pool, user="api@example.com"))
        self.assertTrue(self.acquire_as(pool, user="reader@example.com"))

    # @feature data-store.slot-pool
    def test_every_guest_counts_against_their_own_address(self):
        pool = self.pool(4, per_user=1)
        self.assertTrue(self.acquire_as(pool, user="reader@example.com"))
        with patch.object(frappe.local, "request_ip", "10.0.0.1", create=True):
            self.assertTrue(self.acquire_as(pool, user="Guest"))
            self.assertIsNone(self.acquire_as(pool, user="Guest"))
        with patch.object(frappe.local, "request_ip", "10.0.0.2", create=True):
            self.assertTrue(self.acquire_as(pool, user="Guest"))

    # @feature data-store.slot-pool
    def test_a_site_alone_on_the_bench_uses_every_slot_and_shares_them_when_another_site_reads(self):
        pool = self.pool(4, per_site=2)
        alone = [self.acquire_as(pool, user=f"u{i}@example.com") for i in range(4)]
        self.assertTrue(all(alone))
        for lease in alone:
            pool.release(lease)

        self.assertTrue(self.acquire_as(pool, site="other.localhost"))
        self.assertTrue(self.acquire_as(pool, user="u1@example.com"))
        self.assertTrue(self.acquire_as(pool, user="u2@example.com"))

        self.assertIsNone(self.acquire_as(pool, user="u3@example.com"))
        self.assertTrue(self.acquire_as(pool, site="other.localhost", user="u9@example.com"))

    # @feature data-store.slot-pool
    def test_a_request_waits_for_a_slot_that_frees_and_no_longer_than_its_wait(self):
        pool = self.pool(1)
        held = self.acquire_as(pool, user="first@example.com")
        threading.Timer(0.3, pool.release, args=(held,)).start()

        start = time.monotonic()
        self.assertTrue(pool.acquire(wait=2))
        self.assertLess(time.monotonic() - start, 1.5)

        start = time.monotonic()
        self.assertIsNone(self.acquire_as(pool, user="second@example.com", wait=0.5))
        self.assertGreaterEqual(time.monotonic() - start, 0.5)
        self.assertEqual(frappe.cache.zcard(frappe.cache.make_key(pool.keys[1], shared=True)), 0)

    # @feature data-store.slot-pool
    def test_a_request_is_turned_away_at_once_when_the_waiting_line_is_full(self):
        pool = self.pool(1, max_waiters=0)
        self.assertTrue(self.acquire_as(pool, user="first@example.com"))

        start = time.monotonic()
        self.assertIsNone(self.acquire_as(pool, user="second@example.com", wait=2))
        self.assertLess(time.monotonic() - start, 0.5)


class TestSingleFlight(IntegrationTestCase):
    def key(self):
        key = f"test:{frappe.generate_hash(length=10)}"
        names = (key, f"{key}:run")
        self.addCleanup(frappe.cache.delete, *(frappe.cache.make_key(name) for name in names))
        return key

    def together(self, *calls):
        """Run each call in its own thread, as requests in other workers would,
        starting them in this order. Returns what each returned or raised."""
        site, conf = frappe.local.site, frappe.local.conf
        outcomes = [None] * len(calls)

        def request(i, call):
            frappe.local.site, frappe.local.conf = site, conf
            try:
                outcomes[i] = call()
            except Exception as e:
                outcomes[i] = e

        threads = []
        for i, call in enumerate(calls):
            threads.append(threading.Thread(target=request, args=(i, call)))
            threads[-1].start()
            time.sleep(0.1)
        for thread in threads:
            thread.join()
        return outcomes

    def slow(self, value, runs, seconds=0.5):
        def run():
            runs.append(value)
            time.sleep(seconds)
            if isinstance(value, Exception):
                raise value
            return value

        return run

    # @feature data-store.single-flight
    def test_callers_that_ask_while_a_run_is_in_flight_wait_for_its_value(self):
        key, runs, waited = self.key(), [], []

        def ask():
            return single_flight(key, self.slow("rows", runs), 60, 5, on_wait=lambda: waited.append(1))

        self.assertEqual(self.together(ask, ask, ask), ["rows"] * 3)
        self.assertEqual((runs, len(waited)), (["rows"], 2))
        # the value stays cached for the next caller
        self.assertEqual(single_flight(key, self.slow("other", runs), 60, 5), "rows")
        self.assertEqual(runs, ["rows"])

    # @feature data-store.single-flight
    def test_a_refresh_skips_the_cached_value_and_joins_a_run_in_flight(self):
        key, runs = self.key(), []
        single_flight(key, lambda: "old", 60, 5)

        outcomes = self.together(
            lambda: single_flight(key, self.slow("new", runs), 60, 5, force=True),
            lambda: single_flight(key, self.slow("again", runs), 60, 5, force=True),
        )

        self.assertEqual((outcomes, runs), (["new", "new"], ["new"]))

    # @feature data-store.single-flight
    def test_when_the_run_fails_one_waiter_runs_it_again_and_the_rest_read_its_value(self):
        key, runs = self.key(), []
        failure = ValueError("the source went away")

        outcomes = self.together(
            lambda: single_flight(key, self.slow(failure, runs), 60, 5),
            lambda: single_flight(key, self.slow("rows", runs), 60, 5),
            lambda: single_flight(key, self.slow("rows", runs), 60, 5),
        )

        self.assertEqual(outcomes, [failure, "rows", "rows"])
        self.assertEqual(runs, [failure, "rows"])

    # @feature data-store.single-flight
    def test_a_run_that_fails_as_a_new_run_would_fails_its_waiters_without_running_again(self):
        key, runs = self.key(), []
        timeout = QueryTimeout("Query execution time exceeded the limit of 1 seconds")

        def ask(value):
            return lambda: single_flight(key, self.slow(value, runs), 60, 5, shared_errors=(QueryTimeout,))

        outcomes = self.together(ask(timeout), ask("rows"), ask("rows"))

        self.assertEqual([type(outcome) for outcome in outcomes], [QueryTimeout] * 3)
        self.assertEqual(str(outcomes[2]), str(timeout))
        self.assertEqual(runs, [timeout])

    # @feature data-store.single-flight data-store.cancel
    def test_a_waiter_whose_reader_left_stops_waiting(self):
        key, runs, asked = self.key(), [], time.monotonic()

        def left():
            if time.monotonic() - asked > 0.5:
                raise QueryCancelled("left")

        outcomes = self.together(
            lambda: single_flight(key, self.slow("rows", runs, 3), 60, 5),
            lambda: single_flight(key, self.slow("rows", runs), 60, 5, check=left),
        )

        self.assertIsInstance(outcomes[1], QueryCancelled)
        self.assertEqual(runs, ["rows"])

    # @feature data-store.single-flight
    def test_a_run_whose_worker_died_is_run_by_a_caller_once_its_lock_expires(self):
        key = self.key()
        # a run that will never end: its worker was killed
        # nosemgrep - the key comes from make_key, which prefixes the site
        frappe.cache.set(frappe.cache.make_key(f"{key}:run"), "dead", px=500)

        start = time.monotonic()
        self.assertEqual(single_flight(key, lambda: "rows", 60, 5), "rows")
        self.assertLess(time.monotonic() - start, 2)
