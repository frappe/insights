# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Plain statements of what a profile measured, worst first.

Each rule reads numbers the profile already holds and states one fact with the
numbers behind it. None of them guesses at a cause the profile did not measure.
"""

from typing import Any

UNITS = {
    "bytes": 1,
    "KiB": 1024,
    "MiB": 1024**2,
    "GiB": 1024**3,
    "TiB": 1024**4,
    "KB": 1000,
    "MB": 1000**2,
    "GB": 1000**3,
}
LARGE_TABLE_ROWS = 1_000_000
DOMINANT_SHARE = 0.3
# below these, a share or a slowdown is noise, not a cost worth a finding
MIN_SCAN_SECONDS = 1.0
MIN_WALL_SECONDS = 1.0
NEAR_LIMIT = 0.8
UNORDERED_READS = 0.8
# a table this small reads everything quickly, whatever its order
MIN_ROW_GROUPS = 10


def derive(report: dict) -> list[dict]:
    env = report.get("environment") or {}
    profiled = [s for s in report.get("statements", []) if (s.get("alone") or {}).get("plan")]
    found = [
        *_threads_take_every_core(env),
        *_chart_errors(report),
        *_live_statements(report),
        *_load(report, env),
        *(f for s in report.get("statements", []) for f in _shared(s)),
    ]
    for s in profiled:
        found += _statement_findings(s, env)
    return sorted(found, key=lambda f: f["severity"], reverse=True)


def _finding(kind: str, severity: int, text: str, **numbers) -> dict:
    return {"kind": kind, "severity": severity, "text": text, **numbers}


def _threads_take_every_core(env: dict) -> list[dict]:
    threads = _int((env.get("duckdb") or {}).get("settings", {}).get("threads"))
    cpus = _cpus(env)
    if not threads or not cpus or threads < cpus:
        return []
    return [
        _finding(
            "threads",
            3,
            f"Every query may use all {threads} threads on {cpus} CPUs.",
            threads=threads,
            cpus=cpus,
        )
    ]


def _statement_findings(s: dict, env: dict) -> list[dict]:
    return [
        *_cores(s, env),
        *_unbounded_scans(s, env),
        *_unordered_dates(s),
        *_memory(s, env),
        *_misestimates(s),
        *_experiments(s),
    ]


def _cores(s: dict, env: dict) -> list[dict]:
    alone, cpus = s["alone"], _cpus(env)
    if not cpus or alone["cores"] < 0.75 * cpus:
        return []
    text = f"Alone, it kept {alone['cores']} of {cpus} CPUs busy for {alone['wall_s']}s."
    return [_finding("cores", 3, text, digest=s["digest"], cores=alone["cores"], wall_s=alone["wall_s"])]


def _unbounded_scans(s: dict, env: dict) -> list[dict]:
    """A scan of a large table that no date filter narrows, and that dominates the statement."""
    rows = {t["table"]: t["rows"] for t in env.get("tables") or [] if isinstance(t, dict)}
    found = []
    for scan in s["alone"]["plan"]["scans"]:
        size = rows.get(scan["table"]) or 0
        if scan["date_bounds"] or scan["share"] < DOMINANT_SHARE or size < LARGE_TABLE_ROWS:
            continue
        if scan["seconds"] < MIN_SCAN_SECONDS:
            continue
        text = (
            f"A scan of {scan['table']} ({size:,} rows) with no date bound took "
            f"{round(scan['share'] * 100)}% of the statement's operator time."
        )
        found.append(
            _finding(
                "unbounded_scan", 4, text, digest=s["digest"], table=scan["table"], filters=scan["filters"]
            )
        )
    return found


def _unordered_dates(s: dict) -> list[dict]:
    found = []
    for layout in s.get("layouts") or []:
        if layout.get("reads", 0) < UNORDERED_READS or layout.get("row_groups", 0) < MIN_ROW_GROUPS:
            continue
        text = (
            f"The bound on {layout['table']}.{layout['column']} still reads "
            f"{round(layout['reads'] * 100)}% of row groups: rows are not stored in date order."
        )
        found.append(_finding("date_order", 3, text, digest=s["digest"], **layout))
    return found


def _memory(s: dict, env: dict) -> list[dict]:
    memory = s["alone"]["memory"]
    limit = _bytes((env.get("duckdb") or {}).get("settings", {}).get("memory_limit"))
    found = []
    if memory["peak_spill_bytes"]:
        mb = round(memory["peak_spill_bytes"] / 1e6)
        found.append(_finding("spill", 3, f"It spilled {mb} MB to disk.", digest=s["digest"]))
    if limit and memory["peak_bytes"] >= NEAR_LIMIT * limit:
        text = f"It peaked at {round(memory['peak_bytes'] / 1e9, 2)} GB, near the {round(limit / 1e9, 2)} GB limit."
        found.append(_finding("memory", 3, text, digest=s["digest"]))
    return found


def _misestimates(s: dict) -> list[dict]:
    wrong = s["alone"]["plan"]["misestimates"]
    if not wrong:
        return []
    text = f"{len(wrong)} operators produced 100x more or fewer rows than DuckDB planned for."
    return [_finding("misestimate", 1, text, digest=s["digest"], operators=wrong[:5])]


def _shared(s: dict) -> list[dict]:
    charts = {u["chart"] for u in s.get("used_by") or []}
    if len(charts) < 2:
        return []
    text = f"{len(charts)} charts run this exact statement, each separately."
    return [_finding("duplicate", 2, text, digest=s["digest"], charts=sorted(charts))]


def _experiments(s: dict) -> list[dict]:
    found = []
    alone = s["alone"]["wall_s"] or 0
    if alone < MIN_WALL_SECONDS:
        return []
    for sweep in (s.get("experiments") or {}).get("concurrency") or []:
        if sweep["copies"] > 1 and alone:
            slowdown = round(sweep["slowest_s"] / alone, 1)
            text = f"With {sweep['copies']} copies at once, each took up to {slowdown}x as long as alone."
            found.append(
                _finding(
                    "concurrency", 2, text, digest=s["digest"], copies=sweep["copies"], slowdown=slowdown
                )
            )
    return found


def _chart_errors(report: dict) -> list[dict]:
    failed = [c for c in report.get("charts") or [] if c.get("error")]
    return [
        _finding(
            "chart_error",
            4,
            f"Chart {c['title'] or c['chart']} failed to build: {c['error']}",
            chart=c["chart"],
        )
        for c in failed
    ]


def _live_statements(report: dict) -> list[dict]:
    live = [s for s in report.get("statements") or [] if not s.get("data_store")]
    if not live:
        return []
    return [_finding("live", 1, f"{len(live)} statements read a live source and were not profiled.")]


def _load(report: dict, env: dict) -> list[dict]:
    load = report.get("load")
    if not load or not load.get("runs"):
        return []
    text = (
        f"Loading all {len(load['runs'])} statements six at a time took {load['wall_s']}s, "
        f"used {load['cores']} CPUs and peaked at {round(load['memory']['peak_bytes'] / 1e9, 2)} GB."
    )
    return [_finding("load", 3, text, errors=load["errors"])]


def _cpus(env: dict) -> float | None:
    host = env.get("host") or {}
    return host.get("cpu_limit") or host.get("cpu_count")


def _int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None  # nosemgrep - a setting that is not a number states no thread count


def _bytes(value: Any) -> int | None:
    """`3.7 GiB` as bytes."""
    try:
        number, unit = str(value).split()
        return int(float(number) * UNITS[unit])
    except (ValueError, KeyError):
        return None  # nosemgrep - a limit in a form DuckDB does not print states no limit
