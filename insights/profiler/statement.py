# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Run one statement on the warehouse and take apart where it spent.

`profile` answers, for one statement run alone: its wall time, the CPU the
process actually burned (so how many cores it took), the peak of DuckDB's
memory by kind while it ran, what spilled to disk, and its plan — every scan
with its filters, every join with its condition and sizes, and each operator
whose row estimate was far off.

The experiments rerun a statement under other conditions: other `threads`,
`preserve_insertion_order` off, N copies at once, or a whole dashboard's
statements at the browser's six-at-a-time.

The plan comes from `EXPLAIN ANALYZE`'s own result rather than
`profiling_output`. The warehouse opens with `enable_external_access = false`,
and asking that connection to write a profile file makes DuckDB 1.4
dereference a null pointer and fail the query. `EXPLAIN ANALYZE` runs the query
in full and keeps its rows inside DuckDB, so what is measured is DuckDB's work,
not the conversion to Python.

`threads` and `preserve_insertion_order` belong to the whole DuckDB instance,
not to one cursor. Changing them affects every connection in this process, so
the experiments run in a background job, and put the old value back.
"""

import json
import re
import threading
import time
from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager, suppress
from itertools import pairwise
from typing import Any

from insights.profiler.recorder import resource_reading

SAMPLE_INTERVAL = 0.05
# operators whose actual rows are this many times off the estimate
MISESTIMATE_FACTOR = 100
MISESTIMATE_MIN_ROWS = 10_000
TOP_OPERATORS = 25
DATE_TYPES = ("DATE", "TIMESTAMP")
COMPARISON = re.compile(r"""^\s*"?([A-Za-z_][\w]*)"?\s*(>=|<=|>|<|=|!=|<>)\s*(.+)$""")
QUOTED = re.compile(r"'([^']*)'")


class MemorySampler(threading.Thread):
    """Polls `duckdb_memory()` while statements run, and keeps the peak.

    Sibling cursors share the instance's buffer manager, so this reads the whole
    instance — every statement in flight in this process, which in a profile
    job is only the ones the job runs.
    """

    def __init__(self, connection, interval: float = SAMPLE_INTERVAL):
        super().__init__(daemon=True)
        self.cursor = connection.cursor()
        self.interval = interval
        self.stop_event = threading.Event()
        self.peak_bytes = 0
        self.peak_by_kind: dict[str, int] = {}
        self.peak_spill_bytes = 0
        self.samples = 0

    def run(self) -> None:
        while not self.stop_event.is_set():
            with suppress(Exception):  # nosemgrep - a lost sample must not fail what it watches
                self._sample()
            self.stop_event.wait(self.interval)

    def _sample(self) -> None:
        rows = self.cursor.execute(
            "SELECT tag, memory_usage_bytes, temporary_storage_bytes FROM duckdb_memory()"
        ).fetchall()
        self.samples += 1
        self.peak_spill_bytes = max(self.peak_spill_bytes, sum(r[2] for r in rows))
        total = sum(r[1] for r in rows)
        if total > self.peak_bytes:
            self.peak_bytes = total
            self.peak_by_kind = {r[0]: r[1] for r in rows if r[1]}

    def result(self) -> dict[str, Any]:
        self.stop_event.set()
        self.join(timeout=5)
        return {
            "peak_bytes": self.peak_bytes,
            "peak_by_kind": self.peak_by_kind,
            "peak_spill_bytes": self.peak_spill_bytes,
            "samples": self.samples,
        }


@contextmanager
def measured(connection) -> Generator[dict, None, None]:
    """Fill the yielded dict with the wall time, process CPU and memory peak of the block."""
    sampler = MemorySampler(connection)
    found: dict = {}
    before = resource_reading()
    started = time.monotonic()
    sampler.start()
    try:
        yield found
    finally:
        wall = time.monotonic() - started
        cpu = resource_reading()["cpu"] - before["cpu"]
        found.update(
            wall_s=round(wall, 3),
            cpu_s=round(cpu, 3),
            cores=round(cpu / wall, 2) if wall else 0,
            memory=sampler.result(),
        )


def run_once(connection, sql: str, max_seconds: float) -> tuple[dict | None, str | None]:
    """Run `EXPLAIN ANALYZE` of one statement on a fresh cursor; answer its plan or its error."""
    cursor = connection.cursor()
    timer = threading.Timer(max_seconds, cursor.interrupt)
    timer.daemon = True
    timer.start()
    try:
        cursor.execute("SET enable_profiling='json'")
        cursor.execute("SET profiling_mode='standard'")
        rows = cursor.execute(f"EXPLAIN ANALYZE {sql.strip().rstrip(';')}").fetchall()
        plan = json.loads(rows[0][-1])
        # a statement DuckDB answers from column statistics alone, such as a
        # count every row passes, runs no operators and renders as
        # `{"result": "error"}` although it succeeded
        return (plan if "children" in plan else None), None
    except Exception as e:
        message = str(e).splitlines()[0] if str(e) else type(e).__name__
        return None, f"timed out after {max_seconds}s" if "interrupt" in message.lower() else message[:500]
    finally:
        timer.cancel()
        with suppress(Exception):  # nosemgrep - the cursor is thrown away with its settings
            cursor.close()


def profile(connection, sql: str, max_seconds: float) -> dict[str, Any]:
    """One statement, alone: what it cost and where in the plan it went."""
    with measured(connection) as cost:
        plan, error = run_once(connection, sql, max_seconds)
    found = {**cost, "error": error, "plan": summarize_plan(plan, connection) if plan else None}
    if plan is None and error is None:
        found["plan_missing"] = "DuckDB answered it without operators to report, from column statistics"
    return found


# --- the plan -----------------------------------------------------------------


def summarize_plan(plan: dict, connection) -> dict[str, Any]:
    """Every operator flattened, then the scans, joins and estimates pulled out."""
    operators: list[dict] = []
    _flatten(plan, operators, depth=0)
    total = sum(op["seconds"] for op in operators) or 1
    for op in operators:
        op["share"] = round(op["seconds"] / total, 3)
    return {
        "operators": len(operators),
        "operator_seconds": round(total, 3),
        "top_operators": sorted(operators, key=lambda op: op["seconds"], reverse=True)[:TOP_OPERATORS],
        "scans": _scans(operators, connection),
        "joins": [_join(op) for op in operators if "JOIN" in op["type"]],
        "misestimates": _misestimates(operators),
    }


def _flatten(node: dict, into: list[dict], depth: int) -> None:
    name = (node.get("operator_name") or "").strip()
    if name and name != "EXPLAIN_ANALYZE":
        into.append(_operator(node, name, depth, len(into)))
    for child in node.get("children") or []:
        _flatten(child, into, depth + 1)


def _operator(node: dict, name: str, depth: int, index: int) -> dict:
    info = node.get("extra_info") if isinstance(node.get("extra_info"), dict) else {}
    children = node.get("children") or []
    return {
        "index": index,
        "depth": depth,
        "operator": name,
        "type": node.get("operator_type") or name,
        "seconds": round(node.get("operator_timing") or 0, 4),
        "rows_out": node.get("operator_cardinality"),
        "rows_in": [c.get("operator_cardinality") for c in children],
        "estimated_rows": _int(info.get("Estimated Cardinality")),
        "info": {k: _short(v) for k, v in info.items() if k != "Estimated Cardinality"},
    }


def _scans(operators: list[dict], connection) -> list[dict]:
    """Each table scan with its filters, and whether one of them bounds a date."""
    scans = []
    for op in operators:
        if op["type"] != "TABLE_SCAN":
            continue
        table = op["info"].get("Table")
        filters = _as_list(op["info"].get("Filters"))
        scans.append(
            {
                "table": table,
                "filters": filters,
                "date_bounds": _date_bounds(connection, table, filters),
                "seconds": op["seconds"],
                "share": op["share"],
                "rows_out": op["rows_out"],
            }
        )
    return sorted(scans, key=lambda s: s["seconds"], reverse=True)


def _join(op: dict) -> dict:
    return {
        "join_type": op["info"].get("Join Type"),
        "conditions": op["info"].get("Conditions"),
        "rows_out": op["rows_out"],
        "rows_in": op["rows_in"],
        "seconds": op["seconds"],
        "share": op["share"],
    }


def _misestimates(operators: list[dict]) -> list[dict]:
    """Operators whose actual rows were far from DuckDB's estimate."""
    found = []
    for op in operators:
        actual, estimate = op["rows_out"] or 0, op["estimated_rows"]
        if estimate is None or max(actual, estimate) < MISESTIMATE_MIN_ROWS:
            continue
        ratio = (actual + 1) / (estimate + 1)
        if ratio >= MISESTIMATE_FACTOR or ratio <= 1 / MISESTIMATE_FACTOR:
            found.append(
                {"operator": op["operator"], "index": op["index"], "estimated": estimate, "actual": actual}
            )
    return found


def _date_bounds(connection, table: str | None, filters: list[str]) -> list[dict]:
    """The filters that compare a date or timestamp column, so can skip blocks."""
    bounds = []
    for text in filters:
        match = COMPARISON.match(text)
        if not match or not table:
            continue
        column, operator, value = match.groups()
        if column_type(connection, table, column).startswith(DATE_TYPES):
            literal = QUOTED.search(value)
            bounds.append(
                {"column": column, "operator": operator, "value": literal.group(1) if literal else value}
            )
    return bounds


def column_type(connection, table: str, column: str) -> str:
    row = (
        connection.cursor()
        .execute(
            "SELECT data_type FROM duckdb_columns() WHERE table_name = ? AND column_name = ? LIMIT 1",
            [table, column],
        )
        .fetchone()
    )
    return row[0] if row else ""


def _as_list(value) -> list[str]:
    if value is None:
        return []
    return [str(v) for v in value] if isinstance(value, list) else [str(value)]


def _short(value) -> Any:
    if isinstance(value, list):
        return [_short(v) for v in value]
    return value[:300] if isinstance(value, str) else value


def _int(value) -> int | None:
    try:
        return int(str(value).replace("~", "").strip())
    except (TypeError, ValueError):
        return None  # nosemgrep - a missing estimate is no estimate


# --- experiments --------------------------------------------------------------


@contextmanager
def instance_setting(connection, name: str, value) -> Generator[None, None, None]:
    """Set an instance-wide DuckDB setting for the block, and put the old value back."""
    cursor = connection.cursor()
    old = cursor.execute(f"SELECT current_setting('{name}')").fetchone()[0]
    cursor.execute(f"SET {name} = {_literal(value)}")
    try:
        yield
    finally:
        cursor.execute(f"SET {name} = {_literal(old)}")


def _literal(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def light_run(connection, sql: str, max_seconds: float) -> dict:
    """The cost of one run, without taking its plan apart."""
    with measured(connection) as cost:
        _, error = run_once(connection, sql, max_seconds)
    return {**cost, "error": error}


def threads_sweep(connection, sql: str, values: list[int], max_seconds: float) -> list[dict]:
    """The same statement under each `threads` value."""
    results = []
    for value in values:
        with instance_setting(connection, "threads", value):
            results.append({"threads": value, **light_run(connection, sql, max_seconds)})
    return results


def insertion_order(connection, sql: str, max_seconds: float) -> dict:
    """The same statement with `preserve_insertion_order` on and off."""
    results = {}
    for value in (True, False):
        with instance_setting(connection, "preserve_insertion_order", value):
            results["on" if value else "off"] = light_run(connection, sql, max_seconds)
    return results


def concurrency_sweep(connection, sql: str, values: list[int], max_seconds: float) -> list[dict]:
    """N copies of the same statement at once, for each N."""
    return [{"copies": n, **together(connection, [sql] * n, n, max_seconds)} for n in values]


def together(connection, statements: list[str], in_flight: int, max_seconds: float) -> dict:
    """Run statements `in_flight` at a time and report each one's wall time and the whole."""

    def timed(sql: str) -> dict:
        started = time.monotonic()
        _, error = run_once(connection, sql, max_seconds)
        return {"wall_s": round(time.monotonic() - started, 3), "error": error}

    with measured(connection) as cost:
        with ThreadPoolExecutor(max_workers=max(1, in_flight)) as pool:
            runs = list(pool.map(timed, statements))
    walls = [r["wall_s"] for r in runs]
    return {
        **cost,
        "runs": runs,
        "slowest_s": max(walls, default=0),
        "average_s": round(sum(walls) / len(walls), 3) if walls else 0,
        "errors": sum(1 for r in runs if r["error"]),
    }


# --- storage layout -----------------------------------------------------------


def date_layout(connection, table: str, column: str, bound: str | None, max_seconds: float = 120) -> dict:
    """How a date column's values sit across the table's row groups.

    A date filter can skip a row group only when that group's values all fall
    outside the bound. That works when rows were written in date order, and
    does nothing when they were not. `reads` is the share of row groups a
    `>=`/`>` bound on `bound` still has to read; the comparison is on the
    stored text, which orders ISO dates and timestamps correctly.
    """
    cursor = connection.cursor()
    timer = threading.Timer(max_seconds, cursor.interrupt)
    timer.start()
    try:
        rows = cursor.execute(
            "SELECT row_group_id, stats FROM pragma_storage_info(?) WHERE column_name = ? ORDER BY row_group_id",
            [table, column],
        ).fetchall()
    finally:
        timer.cancel()
    groups = _row_group_ranges(rows)
    return _layout(groups, bound)


def _row_group_ranges(rows: list) -> list[tuple[str, str]]:
    """One (min, max) per row group, merged across its segments."""
    ranges: dict[int, tuple[str, str]] = {}
    for group, stats in rows:
        found = re.search(r"Min: ([^,\]]+), Max: ([^\]]+)\]", stats or "")
        if not found:
            continue
        low, high = found.group(1).strip(), found.group(2).strip()
        old = ranges.get(group)
        ranges[group] = (min(old[0], low), max(old[1], high)) if old else (low, high)
    return [ranges[g] for g in sorted(ranges)]


def _layout(groups: list[tuple[str, str]], bound: str | None) -> dict:
    if not groups:
        return {"row_groups": 0}
    in_order = sum(1 for a, b in pairwise(groups) if b[0] >= a[0])
    layout = {
        "row_groups": len(groups),
        # one row group has no order to measure
        "in_date_order": round(in_order / (len(groups) - 1), 3) if len(groups) > 1 else None,
        "first": groups[0][0],
        "last": max(g[1] for g in groups),
    }
    if bound:
        layout["reads"] = round(sum(1 for _, high in groups if high >= bound) / len(groups), 3)
    return layout
