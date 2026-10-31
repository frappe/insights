# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import os
import tempfile
import threading
import time
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from insights.resources import ResourcePool, web_tier_setting


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


class TestWebTierSettings(IntegrationTestCase):
    # @feature data-store.time-limit
    def test_the_web_tier_is_read_from_the_command_line_then_its_config_file(self):
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as config:
            config.write("import os\nworkers = 8\nthreads = 4\ntimeout = 120\nbind = '0.0.0.0'\n")
        self.addCleanup(os.unlink, config.name)

        with patch.dict(os.environ, {"SERVER_SOFTWARE": "gunicorn/23.0.0"}):
            with patch("sys.argv", ["gunicorn", "-c", config.name, "--threads=2", "frappe.app:application"]):
                self.assertEqual(
                    [web_tier_setting(name) for name in ("workers", "threads", "timeout")], [8, 2, 120]
                )
            with patch("sys.argv", ["gunicorn", "-c", "/nonexistent.py", "-t90", "frappe.app:application"]):
                self.assertEqual((web_tier_setting("timeout"), web_tier_setting("workers")), (90, 1))

        with patch.dict(os.environ, {"SERVER_SOFTWARE": "Werkzeug/3.0"}):
            self.assertIsNone(web_tier_setting("timeout"))
