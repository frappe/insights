# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""The grain a date column is grouped by when nobody named one.

Two readers ask it: a drill's breakdown of a segment, and an axis chart whose
date axis is at the `auto` grain. Both answer it the same way, from the span of
the rows about to be grouped, and differ only in how many buckets they fit it
into.
"""

from datetime import date, datetime, time, timedelta

from frappe.utils import get_datetime

AUTO = "auto"

SECOND = 1
MINUTE = 60 * SECOND
HOUR = 60 * MINUTE
DAY = 24 * HOUR
WEEK = 7 * DAY
MONTH = 30 * DAY
QUARTER = 91 * DAY
YEAR = 365 * DAY

# Every grain an ordered column can be grouped by, coarsest last, against the
# length the derivation reckons it in. One table does both jobs: it is the
# order a derived grain coarsens through, and it is what a caller-named grain is
# checked against. A `Time` has no date part, so the calendar grains cannot
# apply to it.
#
# The lengths are deliberately approximate. They only decide which grain a span
# lands on, never a bucket boundary, which the engine's calendar owns. A grain
# with no length is one a reader may ask for and the derivation will never pick:
# a second-by-second breakdown reads as noise at any span, and which year a
# business counts by is its own decision rather than a consequence of how much
# time a segment covers. A `Date` has no time part, so it lists no sub-day grain
# at all: the engine cannot truncate one to an hour.
GRAINS = {
    "Date": {
        "day": DAY,
        "week": WEEK,
        "month": MONTH,
        "quarter": QUARTER,
        "year": YEAR,
        "fiscal_year": None,
        "fiscal_quarter": None,
    },
    "Datetime": {
        "second": None,
        "minute": MINUTE,
        "hour": HOUR,
        "day": DAY,
        "week": WEEK,
        "month": MONTH,
        "quarter": QUARTER,
        "year": YEAR,
        "fiscal_year": None,
        "fiscal_quarter": None,
    },
    "Time": {"second": SECOND, "minute": MINUTE, "hour": HOUR},
}

# the two ends of the span a grain is derived from, named so the aggregate
# that reads them can be told apart from anything the surface already includes
SPAN_START = "drill_span_start"
SPAN_END = "drill_span_end"


def derived_grain(grains: dict, seconds: float, buckets: int) -> str:
    """The finest grain whose buckets fit the span into `buckets` of them.

    Coarsen until they do: a span that starts partway through a bucket spills
    into another. Nothing coarser than the last grain exists, so a span that
    outgrows it gets that one.
    """
    ladder = {grain: length for grain, length in grains.items() if length}

    for grain, length in ladder.items():
        if seconds / length + 1 <= buckets:
            return grain

    return list(ladder)[-1]


def span_seconds(chart, operations: list[dict], column: dict, adhoc_filters, force: bool = True) -> float:
    """How much time the rows `operations` return cover on `column`.

    One aggregate over the rows about to be grouped: so drilling one month of a
    ten-year series gets a grain that fits the month, and a chart under a
    dashboard filter gets one that fits the filter.
    """
    measures = [
        {
            "measure_name": name,
            "column_name": column["name"],
            "aggregation": aggregation,
            "data_type": column["type"],
        }
        for name, aggregation in ((SPAN_START, "min"), (SPAN_END, "max"))
    ]
    query = chart.get_query(
        operations=[*operations, {"type": "summarize", "measures": measures, "dimensions": []}]
    )
    rows = query.execute(adhoc_filters=adhoc_filters, page_size=1, force=force, include_sql=False)["rows"]
    ends = rows[0] if rows else {}

    start, end = ends.get(SPAN_START), ends.get(SPAN_END)
    if start is None or end is None:
        return 0

    return abs((moment(end) - moment(start)).total_seconds())


def moment(value) -> datetime:
    """A value read off an ordered column, as one point on a line.

    A `Time` comes back as an offset into a day rather than a moment, which
    subtraction will not mix with the rest, and which day it is offset into
    does not matter to a difference.
    """
    if isinstance(value, timedelta):
        return datetime.min + value
    if isinstance(value, datetime):
        return value
    if isinstance(value, time):
        return datetime.combine(datetime.min, value)
    if isinstance(value, date):
        return datetime.combine(value, time.min)

    return get_datetime(str(value))
