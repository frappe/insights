# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Collect the statements a chart runs, without running them.

The execution log keeps only what succeeded, and only what someone ran
recently. A dashboard that fails every chart is in it nowhere. So the profiler
asks the reader's own code path to load each chart, with the dashboard's
default filters and Period, and `execute_ibis_query` hands each statement here
instead of running it. What comes back is what a reader's load would run: the
main query, a Number card's sparkline, a table's row count.
"""

from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar

_statements: ContextVar[list | None] = ContextVar("insights_profiler_capture", default=None)


@contextmanager
def capturing() -> Generator[list[dict], None, None]:
    """Collect, rather than run, every statement executed inside the block."""
    collected: list[dict] = []
    token = _statements.set(collected)
    try:
        yield collected
    finally:
        _statements.reset(token)


def take(sql: str, *, data_store: bool, reference: str | None) -> bool:
    """Keep `sql` if a capture is open, and answer whether the caller must not run it."""
    collected = _statements.get()
    if collected is None:
        return False
    collected.append({"sql": sql, "data_store": data_store, "reference": reference})
    return True
