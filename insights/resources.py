# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""What this server may spend, and a pool that hands out a share of it.

Written against Frappe's own APIs only (`frappe.cache`, `frappe.conf`), so that it
can move into Frappe as it is.
"""

import ast
import os
import random
import sys
import time
import uuid
from functools import cache

import frappe
from frappe.utils import cint

CGROUP_ROOT = "/sys/fs/cgroup"

# gunicorn's own defaults, for a setting neither the command line nor the config file sets
GUNICORN_DEFAULTS = {"workers": 1, "threads": 1, "timeout": 30}
GUNICORN_FLAGS = {"workers": ("-w", "--workers"), "threads": ("--threads",), "timeout": ("-t", "--timeout")}


def cpu_budget() -> float:
    """The cores this process may use: its CPU affinity, under any cgroup quota.

    `os.cpu_count()` counts the host's cores, which a container or a systemd
    unit may not be allowed to use. Site config `cpu_budget` overrides it.
    """
    if override := frappe.conf.get("cpu_budget"):
        return float(override)
    return _cpu_budget()


@cache
def _cpu_budget() -> float:
    cores = float(len(os.sched_getaffinity(0)))
    for folder in _cgroup_folders():
        quota = _read_cgroup(folder, "cpu.max")
        if quota and quota[0] != "max":
            cores = min(cores, int(quota[0]) / int(quota[1]))
    return cores


def memory_budget() -> int:
    """The bytes of RAM this process may use: the host's, under any cgroup limit.

    Site config `memory_budget` (bytes) overrides it.
    """
    if override := frappe.conf.get("memory_budget"):
        return int(override)
    return _memory_budget()


@cache
def _memory_budget() -> int:
    memory = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    for folder in _cgroup_folders():
        limit = _read_cgroup(folder, "memory.max")
        if limit and limit[0] != "max":
            memory = min(memory, int(limit[0]))
    return memory


def _cgroup_folders() -> list[str]:
    """This process's cgroup v2 folder and its ancestors: a limit set on a parent
    slice binds every unit under it."""
    try:
        with open("/proc/self/cgroup") as f:  # nosemgrep - a fixed kernel file, no user input
            line = next((line for line in f if line.startswith("0::")), None)
    except OSError:
        return []  # nosemgrep - no cgroup file means no cgroup limit
    if not line:
        return []
    path = line.strip()[3:].strip("/")
    parts = path.split("/") if path else []
    return [os.path.join(CGROUP_ROOT, *parts[:i]) for i in range(len(parts), -1, -1)]


def _read_cgroup(folder: str, name: str) -> list[str] | None:
    try:
        # nosemgrep - cgroup files under /sys/fs/cgroup, no user input
        with open(os.path.join(folder, name)) as f:
            return f.read().split()
    except (OSError, ValueError):
        return None  # nosemgrep - a controller that is not enabled sets no limit


def web_tier_setting(name: str) -> int | None:
    """A gunicorn setting (`workers`, `threads` or `timeout`) of the web tier this
    process serves, or `None` outside gunicorn.

    Read from the command line, then from the config file, as gunicorn reads
    them. Benches set `-w` and `--threads` on the command line; a server may set
    them in `gunicorn.conf.py` instead, where `frappe.concurrency_limiter`
    does not look. A worker is forked from the master, so `sys.argv` is the
    master's command line.
    """
    if not os.environ.get("SERVER_SOFTWARE", "").startswith("gunicorn"):
        return None
    return _gunicorn_settings(tuple(sys.argv)).get(name, GUNICORN_DEFAULTS[name])


@cache
def _gunicorn_settings(argv: tuple[str, ...]) -> dict:
    settings = {}
    config = _flag_value(argv, "-c", "--config") or "gunicorn.conf.py"
    if not config.startswith("python:"):
        settings.update(_literal_assignments(config))
    for name, flags in GUNICORN_FLAGS.items():
        if (value := _flag_value(argv, *flags)) is not None:
            settings[name] = cint(value)
    return settings


def _flag_value(argv, *flags) -> str | None:
    for i, arg in enumerate(argv):
        for flag in flags:
            if arg == flag and i + 1 < len(argv):
                return argv[i + 1]
            if arg.startswith(f"{flag}="):
                return arg.split("=", 1)[1]
    return None


def _literal_assignments(path: str) -> dict:
    """The integer settings a gunicorn config file assigns as literals. A setting
    it computes is left to the defaults: running the file here would run its
    hooks a second time."""
    try:
        with open(path) as f:  # nosemgrep - the config file gunicorn itself loaded, named on its command line
            tree = ast.parse(f.read())
    except (OSError, SyntaxError, ValueError):
        return {}  # nosemgrep - a config file gunicorn could not have read sets nothing, so its defaults hold
    settings = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in GUNICORN_DEFAULTS and isinstance(node.value, ast.Constant):
                if isinstance(node.value.value, int | float) and not isinstance(node.value.value, bool):
                    settings[name] = int(node.value.value)
    return settings


# Leases, not tokens: each holder is a member of a sorted set scored by its
# deadline, and every call first drops the members past theirs. A worker killed
# mid-request leaves a member that expires, not a token that is gone. Nothing is
# initialised, so two processes cannot both fill a pool, and the capacity a call
# passes is the one it is checked against.
#
# A site may hold more than its share while no other site holds or waits, so a
# single-site bench keeps the whole pool.
#
# Returns 1 when the lease is taken, 0 when the caller is now (or still) waiting,
# -1 when it may not wait.
ACQUIRE_SCRIPT = """
local leases, waiters = KEYS[1], KEYS[2]
local member, site_prefix, user_prefix = ARGV[1], ARGV[2], ARGV[3]
local capacity, per_site, per_user = tonumber(ARGV[4]), tonumber(ARGV[5]), tonumber(ARGV[6])
local lease_ms, wait_ms, max_waiters = tonumber(ARGV[7]), tonumber(ARGV[8]), tonumber(ARGV[9])

local t = redis.call('TIME')
local now = tonumber(t[1]) * 1000 + math.floor(tonumber(t[2]) / 1000)
redis.call('ZREMRANGEBYSCORE', leases, '-inf', now)
redis.call('ZREMRANGEBYSCORE', waiters, '-inf', now)

local function starts(s, prefix) return string.sub(s, 1, #prefix) == prefix end

local held, site_held, user_held, other_site = 0, 0, 0, false
for _, m in ipairs(redis.call('ZRANGE', leases, 0, -1)) do
    held = held + 1
    if starts(m, user_prefix) then user_held = user_held + 1 end
    if starts(m, site_prefix) then site_held = site_held + 1 else other_site = true end
end
local queue = redis.call('ZRANGE', waiters, 0, -1)
local waiting, user_waiting = 0, 0
for _, m in ipairs(queue) do
    if m ~= member then
        waiting = waiting + 1
        if starts(m, user_prefix) then user_waiting = user_waiting + 1 end
        if not starts(m, site_prefix) then other_site = true end
    end
end

local site_capacity = capacity
if other_site then site_capacity = per_site end
if held < capacity and site_held < site_capacity and user_held < per_user then
    local deadline = now + lease_ms
    redis.call('ZADD', leases, deadline, member)
    redis.call('ZREM', waiters, member)
    local last = redis.call('ZRANGE', leases, -1, -1, 'WITHSCORES')
    redis.call('PEXPIREAT', leases, math.max(deadline, tonumber(last[2])))
    return 1
end

if redis.call('ZSCORE', waiters, member) then return 0 end
if wait_ms <= 0 or waiting >= max_waiters or user_waiting >= per_user then return -1 end
redis.call('ZADD', waiters, now + wait_ms, member)
redis.call('PEXPIRE', waiters, wait_ms + 1000)
return 0
"""

RELEASE_SCRIPT = """
redis.call('ZREM', KEYS[1], ARGV[1])
redis.call('ZREM', KEYS[2], ARGV[1])
return 1
"""

POLL_INTERVAL = 0.1

# a lease taken while Redis was unreachable: the pool lets the work through
# rather than fail every request
UNLIMITED = "unlimited"


class ResourcePool:
    """At most `capacity` holders across every process on this Redis.

    `per_site` and `per_user` cap one site's and one user's holders. A site's cap
    applies only while another site holds or waits. A lease that is not released
    is dropped after `lease_seconds`.
    """

    def __init__(
        self,
        name: str,
        capacity: int,
        *,
        per_site: int | None = None,
        per_user: int | None = None,
        max_waiters: int | None = None,
        lease_seconds: float = 120,
    ):
        self.name = name
        self.capacity = max(1, int(capacity))
        self.per_site = max(1, int(per_site or self.capacity))
        self.per_user = max(1, int(per_user or self.capacity))
        self.max_waiters = max(0, int(self.capacity if max_waiters is None else max_waiters))
        self.lease_seconds = lease_seconds

    @property
    def keys(self) -> list[str]:
        return [f"resource_pool:{self.name}:leases", f"resource_pool:{self.name}:waiters"]

    def acquire(self, wait: float = 0) -> str | None:
        """Take a lease, waiting up to `wait` seconds for one. Returns the lease,
        or `None` when the pool stayed full or the waiting line was full too."""
        site = frappe.local.site
        user = holder_name()
        lease = f"{site}|{user}|{uuid.uuid4().hex}"
        deadline = time.monotonic() + wait
        while True:
            remaining = max(0.0, deadline - time.monotonic())
            try:
                taken = self._run(
                    ACQUIRE_SCRIPT,
                    lease,
                    f"{site}|",
                    f"{site}|{user}|",
                    self.capacity,
                    self.per_site,
                    self.per_user,
                    int(self.lease_seconds * 1000),
                    int(remaining * 1000),
                    self.max_waiters,
                )
            except Exception:
                frappe.log_error(f"ResourcePool({self.name}): Redis unavailable, not limiting")
                return UNLIMITED
            if taken == 1:
                return lease
            if taken == -1 or not remaining:
                self.release(lease)
                return None
            # jittered, so the waiters do not all ask in the same instant
            time.sleep(min(remaining, POLL_INTERVAL * (0.5 + random.random())))

    def release(self, lease: str) -> None:
        if lease == UNLIMITED:
            return
        try:
            self._run(RELEASE_SCRIPT, lease)
        except Exception:
            frappe.log_error(f"ResourcePool({self.name}): could not release {lease}")

    def holders(self) -> list[str]:
        """The leases held now, including expired ones not yet dropped."""
        key = frappe.cache.make_key(self.keys[0], shared=True)
        return [m.decode() for m in frappe.cache.zrange(key, 0, -1)]

    def _run(self, script: str, *args):
        keys = [frappe.cache.make_key(key, shared=True) for key in self.keys]
        return frappe.cache.eval(script, len(keys), *keys, *args)


def holder_name() -> str:
    """Whose share a request counts against: the user, or for a guest the address,
    because every guest is the same user."""
    user = frappe.session.user if getattr(frappe.local, "session", None) else "Guest"
    if user == "Guest":
        return f"Guest:{getattr(frappe.local, 'request_ip', None) or ''}"
    return user


def server_busy(retry_after: int):
    """The error a full pool answers with: a 503 the client can retry."""
    if (headers := getattr(frappe.local, "response_headers", None)) is not None:
        headers.set("Retry-After", str(retry_after))
    exc = frappe.exceptions.ServiceUnavailableError(
        frappe._("Server is busy. Please try again in a few seconds.")
    )
    exc.retry_after = retry_after
    return exc
