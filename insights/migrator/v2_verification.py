"""Decide whether a migrated query still returns what the v2 query returned.

Coverage says a thing was translated. Only a diff says it was translated
*correctly*, so this module runs both sides and compares the two frames.

**v2's answer needs no v2 runtime.** v2 compiled every query and stored the
statement in the `sql` column of `tabInsights Query` - 1944 of 2061 non-script
rows have one. That stored statement is v2's ground truth, and the v3 ibis
backend for the same data source runs it verbatim: `backend.sql(stored_sql)`
accepts the backticks, the aliases with spaces, and a trailing-space column name
like `"Count of records "` exactly as MariaDB wrote them. Nothing here imports
v2 code, so the check keeps working after the v2 app is removed - which is the
state the migrator is built for.

Both sides go through the same connection object. `_get_ibis_backend` caches one
backend per data source and sets `time_zone='+00:00'` on it, so the v2 statement
and the v3 query read the same session, the same collation and the same clock.
Comparing across two connections would have made the timezone a variable.

Not every query is worth executing, and the reason differs by kind:

- **builder** - the only real translation. v2's SQL and v3's operations were
  produced by different routes, so agreement is evidence. `check` is
  `translation`.
- **sql** - the SQL floor stores v2's own statement as the single `sql`
  operation, so v3 runs the same text v2 ran. Equality is a tautology about the
  translation and only proves that both sides execute and that the v2 data
  source resolved to a v3 one holding the same rows. `check` is `identity`, and
  a report must not let it inflate a pass rate.
- **code** - a script query has no SQL on either side. v2 ran Python that
  returned a frame; the migrator copies that script verbatim. Nothing runs, not
  even to read its columns: building a code query executes the script and writes
  a temp table into the data store, and a verification must not change the thing
  it verifies. This is the one blind spot, and the report names it.
- A query that cannot run for any other reason still gets a static column check:
  `plan.columns_by_query` holds what v2's spec said the query returned, and the
  v3 query declares its columns without fetching a row.
- **none** - nothing was emitted. There is no v3 query to run.
- A query whose v2 data source is the **Query Store** is not runnable either:
  its stored SQL selects from v2's own result store, which v3 has no counterpart
  for. The v3 query reads the migrated upstream query instead, which is the
  point, but it makes the two statements incomparable.

Every comparison rule is stated in `compare_frames`. The one that matters most
is the verdict: `different` means a human has to look, so a difference the
translators already reported as a gap must not land there. `EXPLAINED_BY`
cross-references the two, and a difference every gap accounts for makes the
verdict `expected`.
"""

import math
from collections import Counter
from dataclasses import dataclass, field, replace
from datetime import date, datetime, time, timedelta, timezone

import frappe

from insights.migrator.v2_workbooks import (
    V3_DATA_SOURCE,
    V3_QUERY,
    MigrationResult,
    load_v2_queries,
)

QUERY_STORE = "Query Store"

DEFAULT_ROW_CAP = 1000
"""Rows fetched from each side. The same number on both, so a row-count
difference is never an artefact of one side being cut shorter than the other."""

SIGNIFICANT_DIGITS = 9
"""How precisely two numbers have to agree.

MariaDB hands back `Decimal`, DuckDB hands back a float, and a sum computed in a
different order does not land on the same last bit, so exact equality reports
noise. Nine significant digits is scale-free - it means the same for a count of
3 and for a revenue total of 4.7e9 - and it sits between the two things it has
to separate: float64 carries ~15-16 significant digits, so real agreement
survives it, while a translation error changes a value by whole units, not by
one part in a billion.

Rounding rather than comparing also makes a number usable as a dictionary key,
which is what lets the unordered comparison be a multiset. So one rule serves
both comparisons instead of a tolerance for one and a grid for the other."""

MAX_REPORTED = 5
"""Differences of one kind listed before the rest are counted."""

# -- verdicts ---------------------------------------------------------------

SAME = "same"
"""No material difference. A name or a dtype difference may still be listed."""

EXPECTED = "expected"
"""Differs, and every difference is accounted for by a gap the translators
already reported. Read the gap, not the diff."""

DIFFERENT = "different"
"""At least one difference nothing predicted. This is the one to look at."""

NOT_RUN = "not_run"
"""Nothing was compared, or the comparison could not settle anything."""

TRANSLATION = "translation"
IDENTITY = "identity"
NONE = "none"

# -- difference kinds -------------------------------------------------------

COLUMN_COUNT = "column_count"
COLUMN_NAME = "column_name"
COLUMN_TYPE = "column_type"
ROW_COUNT = "row_count"
ROW_MEMBERSHIP = "row_membership"
CELL = "cell"

MATERIAL_KINDS = frozenset({COLUMN_COUNT, ROW_COUNT, ROW_MEMBERSHIP, CELL})
"""The kinds that mean the data differs.

A name difference is not one. v3 puts every mutated name through
`ibis_utils.sanitize_name`, so a v2 label with a space or a trailing space comes
back lowercased and underscored while the values under it are untouched. A dtype
difference is not one either: the same date read through two backends is a
`date` on one side and a `Timestamp` on the other and the same day on both. Both
are reported, separately, because a chart names its column and a rename can
still break it - they just do not mean the numbers moved."""

# A gap kind, and the difference kinds it accounts for. Cross-referencing the
# two is what keeps the verifier from crying wolf over a divergence the
# translators already named.
EXPLAINED_BY = {
    # v2 selected a numeric column without grouping by it, which only MySQL's
    # loose grouping allowed. v3 groups by it, so the result is finer: more
    # rows, and a different value in every aggregate.
    "grouped_loose_column": (ROW_COUNT, ROW_MEMBERSHIP, CELL, COLUMN_TYPE),
    # v2 formatted "Month of Year" as "January"; v3's month() returns 1.
    "granularity_part_type": (CELL, COLUMN_TYPE),
    "unknown_granularity": (CELL, COLUMN_TYPE, COLUMN_NAME),
    "ignored_granularity": (CELL, COLUMN_TYPE),
    # v2 replaced the column in place; v3 lands the running total in a
    # sanitized name beside the original.
    "cumulative_column_renamed": (COLUMN_COUNT, COLUMN_NAME, CELL),
    # the running total follows an order the database is free to change
    "cumulative_without_order": (CELL, ROW_MEMBERSHIP),
    "legacy_column_list": (COLUMN_COUNT, COLUMN_NAME),
    "dropped_column": (COLUMN_COUNT, COLUMN_NAME, CELL),
    "dropped_filter": (ROW_COUNT, ROW_MEMBERSHIP, CELL),
    "broken_filter": (ROW_COUNT, ROW_MEMBERSHIP, CELL),
    "unknown_operator": (ROW_COUNT, ROW_MEMBERSHIP, CELL),
    "unknown_aggregation": (CELL,),
    "unknown_join_type": (ROW_COUNT, ROW_MEMBERSHIP, CELL),
    "invalid_join": (ROW_COUNT, ROW_MEMBERSHIP, CELL),
    # stripping a table qualifier off a SQL fragment had to guess a column
    "ambiguous_fragment": (CELL, ROW_COUNT, ROW_MEMBERSHIP),
    "unsupported_transform": (COLUMN_COUNT, COLUMN_NAME, ROW_COUNT, ROW_MEMBERSHIP, CELL),
    "dropped_transform": (COLUMN_COUNT, COLUMN_NAME, ROW_COUNT, ROW_MEMBERSHIP, CELL),
    "script_result_shape": (COLUMN_COUNT, COLUMN_NAME),
}


NULL = "\x00null"
"""One spelling for missing. The two sides disagree about the rest of them:
`execute_ibis_query` replaces `NaT` and `NaN` with `None` on its way out, and a
frame read straight off a backend keeps them, so `None`, `NaN`, `NaT` and
`pd.NA` all have to mean the same thing here."""


# -- the result -------------------------------------------------------------


@dataclass(frozen=True)
class Difference:
    """One way the two frames disagree."""

    kind: str
    detail: str
    column: str = ""
    explained_by: str = ""
    """The gap kind that predicted this, or empty when nothing did."""

    @property
    def expected(self) -> bool:
        return bool(self.explained_by)

    @property
    def material(self) -> bool:
        return self.kind in MATERIAL_KINDS


@dataclass
class QueryVerification:
    """One v2 query, its v3 counterpart, and whether they agree."""

    source: str
    """The v2 query docname."""

    target: str | None = None
    """The v3 query docname, or None when the migration wrote none."""

    kind: str = "none"
    verdict: str = NOT_RUN
    check: str = NONE
    """What agreement would prove: `translation`, `identity`, or `none`."""

    reason: str = ""
    differences: list[Difference] = field(default_factory=list)
    v2_rows: int | None = None
    v3_rows: int | None = None

    @property
    def unexpected(self) -> list[Difference]:
        return [d for d in self.differences if d.material and not d.expected]

    @property
    def title(self) -> str:
        return f"{self.source} -> {self.target or '(nothing)'}"


@dataclass
class VerificationReport:
    """Every query of one migration, verified."""

    dashboard: str
    workbook: str | None = None
    verifications: list[QueryVerification] = field(default_factory=list)
    row_cap: int = DEFAULT_ROW_CAP

    @property
    def counts(self) -> dict:
        counts = dict.fromkeys((SAME, EXPECTED, DIFFERENT, NOT_RUN), 0)
        for check in self.verifications:
            counts[check.verdict] += 1
        return counts

    @property
    def trustworthy(self) -> bool:
        """No query differs in a way nothing predicted.

        Deliberately not "everything was verified": a `code` query that could
        not be run is a known blind spot, and the report names it. Read
        `counts[NOT_RUN]` alongside this.
        """
        return not any(check.verdict == DIFFERENT for check in self.verifications)

    @property
    def report(self) -> str:
        return format_verification(self)


# -- canonical values -------------------------------------------------------


def _is_null(value) -> bool:
    if value is None:
        return True
    try:
        if isinstance(value, float) and math.isnan(value):
            return True
    except TypeError:
        pass
    # pandas spells missing four ways; `pd.isna` knows all of them, and returns
    # an array for a container, which is never a cell here.
    try:
        import pandas as pd

        result = pd.isna(value)
        return bool(result) if isinstance(result, bool | int | float) else False
    except (TypeError, ValueError, ImportError):
        return False


def _canonical(value):
    """One comparable form for a cell, whichever backend produced it.

    A `Decimal` from MariaDB and a float from DuckDB have to land on the same
    value; so do a `date` and the `Timestamp` at midnight that the other backend
    returns for the same column. A tz-aware timestamp is converted to UTC and
    stripped, because the connection already pins the session to UTC and only
    the driver decides whether to say so.
    """
    if _is_null(value):
        return NULL

    if isinstance(value, bytes | bytearray):
        return value.decode("utf-8", "replace")

    if isinstance(value, datetime):
        if value.tzinfo is not None:
            value = value.astimezone(timezone.utc).replace(tzinfo=None)
        if (value.hour, value.minute, value.second, value.microsecond) == (0, 0, 0, 0):
            return value.date().isoformat()
        return value.isoformat(sep=" ")

    if isinstance(value, date):
        return value.isoformat()

    if isinstance(value, time | timedelta):
        return str(value)

    number = _as_number(value)
    if number is not None:
        return number

    return str(value)


def _as_number(value):
    """A float rounded to `SIGNIFICANT_DIGITS`, or None when it is not a number.

    A boolean goes through it too, on purpose: one backend returns a `bool`
    column where the other returns 0 and 1, and the two say the same thing. The
    dtype difference is reported on its own.
    """
    if isinstance(value, str):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number):
        return NULL
    if math.isinf(number):
        return number
    return float(f"{number:.{SIGNIFICANT_DIGITS}g}")


def _normal(name: str) -> str:
    """A column name with every difference `sanitize_name` can introduce removed.

    v3 runs a mutated `new_name` through `ibis_utils.sanitize_name`, which
    strips, lowercases and turns a space into an underscore. A v2 label like
    `"Count of records "` and the v3 `count_of_records` are the same column
    named twice, so the comparison must not read that as data moving.
    """
    text = str(name).strip().lower()
    for char in " -./()":
        text = text.replace(char, "_")
    return text.strip("_")


# -- comparing --------------------------------------------------------------


def compare_frames(left, right, *, ordered: bool = False) -> list[Difference]:
    """Every way two result frames disagree. Pure: two frames in, a list out.

    `left` is v2's answer and `right` is v3's. The rules, and why each one:

    - **Columns line up by position when there are as many of them.** v2 named a
      column by its label, spaces and all; v3 sanitizes a mutated name and a
      cumulative sum lands in a renamed column beside the original. Position is
      the only thing both sides preserve. A name that differs at the same
      position is reported as `column_name` and nothing more - it is not a data
      difference. When the counts differ there is no position to trust, so the
      columns are matched by normalised name and whatever is left over is
      reported as `column_count`.
    - **Rows are a multiset unless `ordered`.** v2 emitted `ORDER BY` only for a
      column with `order` set, so most v2 results came back in whatever order
      the engine chose. Comparing those positionally would report a difference
      on every query that groups.
    - **A cell is compared as its canonical value**, so `Decimal("3")` equals
      `3.0`, `NaN` equals `None`, and a date equals the timestamp at its
      midnight. See `_canonical` and `SIGNIFICANT_DIGITS`.
    - **A dtype difference is reported and does not count**, because two
      backends spell the same day with two dtypes.
    """
    differences: list[Difference] = []
    pairs = _align_columns(left, right, differences)

    for left_name, right_name in pairs:
        if _normal(left_name) != _normal(right_name):
            differences.append(
                Difference(
                    COLUMN_NAME,
                    f"v2 called it {left_name!r}, v3 calls it {right_name!r}",
                    column=str(left_name),
                )
            )
        left_type, right_type = str(left.dtypes[left_name]), str(right.dtypes[right_name])
        if left_type != right_type:
            differences.append(
                Difference(
                    COLUMN_TYPE,
                    f"v2 returned {left_type}, v3 returns {right_type}",
                    column=str(left_name),
                )
            )

    differences += _compare_rows(left, right, pairs, ordered=ordered)
    return differences


def _align_columns(left, right, differences: list[Difference]):
    """Pair the two frames' columns, reporting the ones that do not pair.

    A column that pairs with nothing is reported and then left out of the row
    comparison. Dropping the whole row comparison instead would hide every
    difference behind one extra column - and an extra column is exactly what
    `cumulative_column_renamed` and the widened grouping produce.
    """
    left_names, right_names = list(left.columns), list(right.columns)

    if len(left_names) == len(right_names):
        return list(zip(left_names, right_names, strict=True))

    by_normal = {}
    for name in right_names:
        by_normal.setdefault(_normal(name), name)

    pairs, only_v2 = [], []
    taken = set()
    for name in left_names:
        match = by_normal.get(_normal(name))
        if match is None or match in taken:
            only_v2.append(str(name))
            continue
        taken.add(match)
        pairs.append((name, match))

    only_v3 = [str(name) for name in right_names if name not in taken]
    differences.append(
        Difference(
            COLUMN_COUNT,
            f"v2 returned {len(left_names)} column(s), v3 returns {len(right_names)}"
            + (f"; only in v2: {', '.join(only_v2)}" if only_v2 else "")
            + (f"; only in v3: {', '.join(only_v3)}" if only_v3 else ""),
        )
    )
    return pairs


def _rows(frame, pairs, side: int) -> list[tuple]:
    columns = [pair[side] for pair in pairs]
    if not columns:
        return []
    return [tuple(_canonical(value) for value in row) for row in frame[columns].itertuples(index=False)]


def _compare_rows(left, right, pairs, *, ordered: bool) -> list[Difference]:
    left_rows, right_rows = _rows(left, pairs, 0), _rows(right, pairs, 1)
    names = [str(pair[0]) for pair in pairs]

    differences = []
    if len(left_rows) != len(right_rows):
        differences.append(
            Difference(ROW_COUNT, f"v2 returned {len(left_rows)} row(s), v3 returns {len(right_rows)}")
        )

    if ordered:
        differences += _compare_in_order(left_rows, right_rows, names)
    else:
        differences += _compare_as_multiset(left_rows, right_rows, names)
    return differences


def _compare_in_order(left_rows, right_rows, names) -> list[Difference]:
    differences, reported, extra = [], 0, 0
    for index, (left_row, right_row) in enumerate(zip(left_rows, right_rows, strict=False)):
        for column, (left_value, right_value) in enumerate(zip(left_row, right_row, strict=True)):
            if left_value == right_value:
                continue
            if reported < MAX_REPORTED:
                differences.append(
                    Difference(
                        CELL,
                        f"row {index}, {names[column]}: v2 {_show(left_value)}, v3 {_show(right_value)}",
                        column=names[column],
                    )
                )
                reported += 1
            else:
                extra += 1
    if extra:
        differences.append(Difference(CELL, f"and {extra} more differing cell(s)"))
    return differences


def _compare_as_multiset(left_rows, right_rows, names) -> list[Difference]:
    left_counts, right_counts = Counter(left_rows), Counter(right_rows)
    only_v2 = left_counts - right_counts
    only_v3 = right_counts - left_counts
    if not only_v2 and not only_v3:
        return []

    header = ", ".join(names)
    detail = f"{sum(only_v2.values())} row(s) only in v2, {sum(only_v3.values())} only in v3 " f"({header})"
    differences = [Difference(ROW_MEMBERSHIP, detail)]
    for label, counts in (("v2", only_v2), ("v3", only_v3)):
        for row, _count in list(counts.items())[:MAX_REPORTED]:
            differences.append(
                Difference(ROW_MEMBERSHIP, f"only in {label}: ({', '.join(_show(v) for v in row)})")
            )
    return differences


def _show(value) -> str:
    return "NULL" if value == NULL else repr(value)


def classify(differences: list[Difference], gap_kinds) -> list[Difference]:
    """Tag each difference with the gap that predicted it, if any.

    A gap is the translator saying "this will not come out the same, and here is
    why". A verifier that reports the consequence as a failure is repeating a
    thing the report already says, in a place reserved for surprises.
    """
    gap_kinds = set(gap_kinds)
    tagged = []
    for difference in differences:
        explained = next(
            (kind for kind in sorted(gap_kinds) if difference.kind in EXPLAINED_BY.get(kind, ())),
            "",
        )
        tagged.append(replace(difference, explained_by=explained))
    return tagged


def verdict_for(differences: list[Difference]) -> str:
    material = [d for d in differences if d.material]
    if not material:
        return SAME
    if all(d.expected for d in material):
        return EXPECTED
    return DIFFERENT


# -- reading the two sides --------------------------------------------------


def _backend(data_source: str):
    return frappe.get_doc(V3_DATA_SOURCE, data_source)._get_ibis_backend()


def sqlglot_dialect(data_source: str) -> str | None:
    """The dialect the stored statement is written in.

    The data source doctype already answers this for the ibis side, so the
    parse here reads the same mapping rather than a second copy of it.
    """
    return frappe.get_doc(V3_DATA_SOURCE, data_source).get_sqlglot_dialect()


def stated_limit(sql: str, dialect: str | None = None) -> int | None:
    """The row limit the stored statement states at its top level, if any."""
    parsed = _parse(sql, dialect)
    if parsed is None:
        return None
    limit = parsed.args.get("limit")
    expression = getattr(limit, "expression", None) if limit is not None else None
    try:
        return int(expression.name)
    except (AttributeError, TypeError, ValueError):
        return None


def states_an_order(sql: str, dialect: str | None = None) -> bool:
    """Whether the stored statement orders its own top-level result.

    v2 emitted `ORDER BY` only when a column carried `order`, so this is the one
    signal that says whether row order is part of the answer. A subquery's order
    is not: `args["order"]` is read off the outermost select alone.
    """
    parsed = _parse(sql, dialect)
    return parsed is not None and parsed.args.get("order") is not None


def _parse(sql: str, dialect: str | None):
    if not sql:
        return None
    try:
        import sqlglot

        return sqlglot.parse_one(sql, read=dialect)
    except Exception:
        # An unparseable statement is not an error here - it only means the
        # order and the limit are unknown, and both default to the cautious
        # reading: unordered, and capped from the outside.
        return None


def v2_answer(sql: str, data_source: str, *, cap: int = DEFAULT_ROW_CAP, dialect: str | None = None):
    """Run v2's own compiled statement through the v3 backend for its source.

    The statement is left as it is wherever possible. A `LIMIT` is appended as
    text rather than by wrapping the statement in a subselect, because MySQL is
    free to drop the `ORDER BY` of a derived table and that would silently turn
    an ordered answer into an unordered one. Only a statement that already has a
    limit too large to fetch, or one that would not parse, is wrapped.
    """
    backend = _backend(data_source)
    limit = stated_limit(sql, dialect)
    parsed = _parse(sql, dialect) is not None

    if parsed and limit is None:
        return backend.sql(f"{sql.strip().rstrip(';')} limit {int(cap)}").to_pandas()
    if parsed and limit <= cap:
        return backend.sql(sql).to_pandas()
    return backend.sql(sql).limit(cap).to_pandas()


def v3_answer(query_name: str, *, cap: int = DEFAULT_ROW_CAP):
    """Execute the migrated query the way the app does.

    `build()` is the doctype's own, so the stored `use_live_connection` decides
    where the query reads. Passing one in would be a claim the document does not
    make - and a builder query built with the flag off imports its source table
    into the data store on the way, which is a copy nobody asked for and a
    strange thing for a verification to create.
    """
    from insights.insights.doctype.insights_data_source_v3.ibis_utils import execute_ibis_query

    document = frappe.get_doc(V3_QUERY, query_name)
    frame, _time_taken = execute_ibis_query(
        document.build(),
        paginate=True,
        page_size=cap,
        cache=False,
        reference_doctype=V3_QUERY,
        reference_name=query_name,
    )
    return frame


def v3_columns(query_name: str) -> list[str]:
    """The column names the migrated query declares, without fetching a row.

    Not free for a `code` query: building one runs the script. See
    `_static_check`.
    """
    return list(frappe.get_doc(V3_QUERY, query_name).build().schema().names)


# -- verifying --------------------------------------------------------------


def verify_query(
    v2_query: dict,
    query_plan,
    target: str | None,
    *,
    data_source: str | None,
    expected_columns=None,
    cap: int = DEFAULT_ROW_CAP,
) -> QueryVerification:
    """Compare one migrated query against the v2 query it came from."""
    check = QueryVerification(
        source=query_plan.source,
        target=target,
        kind=query_plan.kind,
        check=TRANSLATION if query_plan.kind == "builder" else NONE,
    )
    gap_kinds = {gap.kind for gap in query_plan.translated.gaps}

    skip = _why_not_run(v2_query, query_plan, target, data_source)
    if skip:
        check.reason = skip
        check.differences = classify(_static_check(target, expected_columns, query_plan.kind), gap_kinds)
        return check

    if query_plan.kind == "sql":
        check.check = IDENTITY

    sql = (v2_query.get("sql") or "").strip().rstrip(";")
    dialect = sqlglot_dialect(data_source)

    try:
        left = v2_answer(sql, data_source, cap=cap, dialect=dialect)
    except Exception as error:
        check.reason = f"v2's stored SQL did not run: {error}"
        return check

    try:
        right = v3_answer(target, cap=cap)
    except Exception as error:
        # The reversed `sum_if` arguments MySQL tolerated and ibis rejects land
        # here, as does any operation the source cannot express.
        check.reason = f"the migrated query did not run: {error}"
        return check

    check.v2_rows, check.v3_rows = len(left), len(right)
    ordered = states_an_order(sql, dialect)
    check.differences = classify(compare_frames(left, right, ordered=ordered), gap_kinds)
    check.verdict = verdict_for(check.differences)

    if check.verdict != SAME and not ordered and len(left) == cap == len(right):
        # Both sides were cut at the cap and neither states an order, so the two
        # samples need not describe the same rows. Agreement would still have
        # meant something; disagreement does not.
        return QueryVerification(
            source=check.source,
            target=check.target,
            kind=check.kind,
            check=check.check,
            reason=f"both sides returned the full {cap}-row cap and neither states an "
            f"order, so the samples need not agree. Re-run with a larger cap",
            differences=check.differences,
            v2_rows=check.v2_rows,
            v3_rows=check.v3_rows,
        )

    return check


def _why_not_run(v2_query: dict, query_plan, target, data_source) -> str:
    """Why this query is not worth executing, or an empty string when it is."""
    if not target:
        return "the migration wrote no v3 query for it"
    if query_plan.kind == "none":
        return "nothing was translated, so there is no query to run"
    if query_plan.kind == "code":
        return (
            "a script query has no SQL on either side: v2 ran Python that returned a "
            "frame, and the migrator copies that script verbatim. Nothing is run, not "
            "even to read its columns - building one executes the script and writes a "
            "temp table into the data store, and a verification must not have that effect"
        )
    if (v2_query.get("data_source") or "") == QUERY_STORE:
        return (
            "its v2 SQL selects from the Query Store, v2's own result store, which v3 "
            "has no counterpart for. The v3 query reads the migrated upstream query instead"
        )
    if not (v2_query.get("sql") or "").strip():
        return "v2 stored no compiled SQL for it, so v2's answer cannot be reproduced"
    if not data_source:
        return "no v3 data source answers to the v2 one, so v2's SQL has nowhere to run"
    return ""


def _static_check(target, expected_columns, kind: str) -> list[Difference]:
    """What can still be said about a query that cannot be executed.

    `DashboardPlan.columns_by_query` records the columns v2's stored spec said
    the query returned. Held against the columns the v3 query declares, it
    catches a lost or renamed column without fetching a row - which is all a
    query whose v2 source is gone can offer.

    A `code` query is left out. Building one is not free: `apply_code` runs the
    script and writes its result into the data store as a temp table, so reading
    its columns would make a verification change the thing it verifies.
    """
    if kind == "code" or not target or not expected_columns:
        return []

    try:
        actual = v3_columns(target)
    except Exception as error:
        return [Difference(COLUMN_COUNT, f"the migrated query would not even build: {error}")]

    wanted = [column["name"] for column in expected_columns]
    if [_normal(name) for name in wanted] == [_normal(name) for name in actual]:
        return []

    missing = [name for name in wanted if _normal(name) not in {_normal(a) for a in actual}]
    added = [name for name in actual if _normal(name) not in {_normal(w) for w in wanted}]
    return [
        Difference(
            COLUMN_COUNT,
            f"v2's spec recorded {wanted}, the v3 query declares {actual}"
            + (f"; missing: {', '.join(missing)}" if missing else "")
            + (f"; added: {', '.join(added)}" if added else ""),
        )
    ]


def verify_migration(
    result: MigrationResult,
    *,
    cap: int = DEFAULT_ROW_CAP,
    queries: dict | None = None,
) -> VerificationReport:
    """Verify every query one dashboard migration wrote.

    `MigrationResult` already holds the mapping this needs: `query_names` says
    which v3 query has to return what each v2 query returned, and
    `plan.columns_by_query` says what v2's spec expected of it. The v2 rows are
    re-read here rather than carried on the result, because a verification is a
    separate act from a migration and may run long after one.
    """
    plan = result.plan
    queries = queries if queries is not None else load_v2_queries(list(plan.query_plans))

    report = VerificationReport(dashboard=plan.source, workbook=result.workbook, row_cap=cap)
    for query_plan in plan.queries:
        v2_query = queries.get(query_plan.source) or {}
        report.verifications.append(
            verify_query(
                v2_query,
                query_plan,
                result.query_names.get(query_plan.source),
                data_source=query_plan.data_source,
                expected_columns=plan.columns_by_query.get(query_plan.source),
                cap=cap,
            )
        )
    return report


# -- reporting --------------------------------------------------------------


def format_verification(report: VerificationReport) -> str:
    """The verification of one migration, top to bottom, for a human."""
    counts = report.counts
    lines = [
        f"{report.dashboard} - verification of {len(report.verifications)} query(s), "
        f"cap {report.row_cap} rows",
        f"  same {counts[SAME]}, expected {counts[EXPECTED]}, "
        f"different {counts[DIFFERENT]}, not run {counts[NOT_RUN]}",
    ]

    for check in report.verifications:
        rows = ""
        if check.v2_rows is not None:
            rows = f" [{check.v2_rows} vs {check.v3_rows} rows]"
        note = "" if check.check == TRANSLATION else f" ({check.check} check)"
        lines.append(f"  {check.verdict.upper():<9} {check.title} - {check.kind}{note}{rows}")
        if check.reason:
            lines.append(f"      {check.reason}")
        for difference in check.differences:
            mark = "!" if difference.material and not difference.expected else "-"
            tag = f" [expected: {difference.explained_by}]" if difference.expected else ""
            lines.append(f"      {mark} {difference.kind}: {difference.detail}{tag}")

    return "\n".join(lines)
