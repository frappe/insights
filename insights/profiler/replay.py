# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Open a dashboard over HTTP the way N readers' browsers would.

This runs on an operator's machine, not on the site, and talks to the site
through `frappectl`, so gunicorn's workers and timeout, the query limiter and
nginx are all part of what it measures. Each reader keeps six chart requests in
flight and retries a 503 with the browser's backoff
(`frontend/src2/query/execution_queue.ts`).

It switches the recorder on first, so the report it saves holds both sides:
what each request saw from outside, and what the server did inside.

    python -m insights.profiler.replay --site insights.frappe.io \\
        --dashboard 6e0d62l68s --readers 2

Run it off-peak. It produces the load it measures.
"""

import argparse
import json
import random
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from statistics import median

IN_FLIGHT = 6
MAX_ATTEMPTS = 8
RETRY_BASE_DELAY = 1.0
MAX_RETRY_DELAY = 8.0


def call(site: str, method: str, **fields) -> tuple[bool, dict | str, float]:
    """One whitelisted call through frappectl: (ok, answer or error text, seconds)."""
    # no site: frappectl reads FRAPPE_SITE, FRAPPE_API_KEY and FRAPPE_API_SECRET
    args = ["frappectl", *(["-s", site] if site else []), "--json", "method", "call", method]
    for key, value in fields.items():
        args += ["-F", f"{key}:={json.dumps(value)}"]
    started = time.monotonic()
    done = subprocess.run(args, capture_output=True, text=True)
    seconds = time.monotonic() - started
    if done.returncode == 0:
        return True, json.loads(done.stdout or "null"), seconds
    return False, (done.stderr or done.stdout).strip()[-600:], seconds


def is_busy(error: str) -> bool:
    return "503" in error or "ServiceUnavailable" in error or "Server is busy" in error


def load_chart(site: str, dashboard: str, chart: str, filters: dict, force: bool) -> dict:
    """One card's load, retried on a 503 as the browser retries it."""
    started = time.time()
    for attempt in range(1, MAX_ATTEMPTS + 1):
        ok, answer, seconds = call(
            site,
            "insights.api.view.get_chart_data",
            chart=chart,
            dashboard=dashboard,
            filters=filters,
            force=force,
        )
        if ok or not is_busy(answer) or attempt == MAX_ATTEMPTS:
            break
        delay = min(RETRY_BASE_DELAY * 2 ** (attempt - 1), MAX_RETRY_DELAY)
        time.sleep(delay * (0.5 + random.random()))
    return {
        "chart": chart,
        "ok": ok,
        "attempts": attempt,
        "last_call_s": round(seconds, 3),
        "wall_s": round(time.time() - started, 3),
        "error": None if ok else answer,
        "started": started,
    }


def open_dashboard(site: str, dashboard: str, charts: list[str], filters: dict, force: bool) -> list[dict]:
    """One reader: every card, six at a time."""
    with ThreadPoolExecutor(max_workers=IN_FLIGHT) as pool:
        return list(pool.map(lambda c: load_chart(site, dashboard, c, filters, force), charts))


def dashboard_cards(site: str, dashboard: str) -> tuple[list[str], dict]:
    """The dashboard's charts in layout order, and the filter state it opens with."""
    ok, answer, _ = call(site, "insights.api.view.get_dashboard", dashboard=dashboard)
    if not ok:
        sys.exit(f"Could not read dashboard {dashboard}: {answer}")
    items = answer.get("items") or []
    if isinstance(items, str):
        items = json.loads(items)
    charts = [i["chart"] for i in items if i.get("type") == "chart" and i.get("chart")]
    filters = {
        i["filter_name"]: {"operator": i["default_operator"], "value": i.get("default_value")}
        for i in items
        if i.get("type") == "filter" and i.get("filter_name") and i.get("default_operator")
    }
    return charts, filters


def call_overhead(site: str) -> float:
    """What one frappectl round trip costs with no work behind it."""
    return median(call(site, "frappe.ping")[2] for _ in range(3))


def summarize(runs: list[list[dict]], overhead: float) -> dict:
    flat = [r for reader in runs for r in reader]
    walls = sorted(r["wall_s"] for r in flat)
    return {
        "requests": len(flat),
        "failed": sum(1 for r in flat if not r["ok"]),
        "retried": sum(1 for r in flat if r["attempts"] > 1),
        "call_overhead_s": round(overhead, 3),
        "card_wall_s": {"median": walls[len(walls) // 2], "max": walls[-1]} if walls else {},
        "errors": sorted({r["error"][:200] for r in flat if r["error"]}),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--site", help="frappectl profile name; omit to use FRAPPE_SITE and an API key")
    parser.add_argument("--dashboard", required=True)
    parser.add_argument("--readers", type=int, default=1)
    parser.add_argument("--force", action="store_true", help="bypass the result cache, as Refresh does")
    parser.add_argument("--out", default=None, help="where to save the JSON report")
    args = parser.parse_args()

    charts, filters = dashboard_cards(args.site, args.dashboard)
    overhead = call_overhead(args.site)
    call(args.site, "insights.api.profiler.start_recording", minutes=60)
    print(
        f"{len(charts)} cards x {args.readers} readers, {IN_FLIGHT} in flight each; call overhead {overhead:.2f}s"
    )

    since = time.time()
    with ThreadPoolExecutor(max_workers=max(1, args.readers)) as pool:
        runs = list(
            pool.map(
                lambda _: open_dashboard(args.site, args.dashboard, charts, filters, args.force),
                range(args.readers),
            )
        )
    until = time.time()

    time.sleep(2)  # let the last end events land
    _, server, _ = call(
        args.site,
        "insights.api.profiler.recording_report",
        since=since,
        until=until,
        dashboard=args.dashboard,
    )
    report = {
        "dashboard": args.dashboard,
        "readers": args.readers,
        "since": since,
        "until": until,
        "client": summarize(runs, overhead),
        "requests": runs,
        "server": server,
    }
    out = args.out or f"replay-{args.dashboard}-{int(since)}.json"
    with open(out, "w") as f:  # nosemgrep - the operator's own --out on their own machine
        json.dump(report, f, indent=2, default=str)
    print(json.dumps(report["client"], indent=2))
    print(f"Full report: {out}")


if __name__ == "__main__":
    main()
