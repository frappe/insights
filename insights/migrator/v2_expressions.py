"""Translate a v2 expression AST into a v3 expression string.

v2 stores a parsed AST beside the raw text of every expression column and filter, so
this is a tree walk and not a parsing problem. v3 evaluates an expression as Python
with every column of the current query bound by its bare name, so a v2 `Column` node
collapses to its column and loses its table.

Three v2 functions have no v3 counterpart, and they do not share one fallback.

`sql` becomes a `Fragment`: a raw SQL string the caller materialises through the
`sql_column` operation, with a reference to that column left behind in the expression.
A fragment can sit anywhere in the tree, which is why the result carries an expression
plus a list of fragments instead of one or the other.

`descendants` and `descendants_and_self` cannot. v2 compiles them to
``field IN (SELECT ... FROM tree WHERE lft >= ...)``, and `sql_column` rejects any
fragment containing a `Select` - it does no permission-aware table binding, so a
subquery would reopen the table-access surface. Resolving the tree to a literal list at
migration time is worse: it works until the user edits the tree, then drifts in
silence. So they are a third outcome, `Outcome.COMPILED_SQL`, reported as a `Blocker`
with no expression at all. The caller falls back to the whole-query compiled SQL.

One function needs its meaning translated rather than its spelling. v2 `between` runs
both bounds through `add_start_and_end_time`, which widens the end to `23:59:59`, so a
row stamped at noon on the last day is inside the range. v3 `is_between` compares the
bounds as given. Renaming alone would drop the last day of every range, quietly, so the
widening is written into the emitted literals instead.

Some v2 expressions did not run in v2 either - a `between` over a bound `getdate()`
cannot read, or a `time_elapsed` unit v2's own list rejected. These are
`Outcome.BROKEN_IN_V2`, not an exception, because the migrator converts a whole
dashboard closure and one query that was already broken must not abort the rest. The
compiled SQL floor cannot rescue them, since v2 never generated any SQL to fall back
to. `TranslationError` is reserved for a mapping this module is missing.

A fragment runs where its original table is not in scope, so table qualifiers are
stripped: ``\\`tabIssue\\`.\\`status\\`` becomes ``\\`status\\``. Stripping is only safe
while one table owns the name. Pass `table_columns` and any column two joined tables
both provide comes back in `ambiguous_columns` rather than being silently guessed.

This module is pure: it imports nothing from frappe and needs no database.
"""

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

# Functions v3 spells exactly as v2 did, with the same argument order.
DIRECT_FUNCTIONS = frozenset(
    {
        "abs",
        "avg",
        "case",
        "ceil",
        "coalesce",
        "concat",
        "contains",
        "count",
        "count_if",
        "distinct_count",
        "distinct_count_if",
        "floor",
        "if_null",
        "is_not_set",
        "is_set",
        "lower",
        "max",
        "min",
        "not_contains",
        "now",
        "replace",
        "round",
        "substring",
        "sum",
        "sum_if",
        "today",
        "upper",
    }
)

# Same meaning, different name. v2 accepted a few aggregations in upper case.
RENAMED_FUNCTIONS = {
    "between": "is_between",
    "in": "is_in",
    "not_in": "is_not_in",
    "timespan": "within",
    "AVG": "avg",
    "COUNT": "count",
    "MAX": "max",
    "MIN": "min",
    "SUM": "sum",
}

# v2 `time_elapsed` is MySQL TIMESTAMPDIFF, which returns `b - a`. v3 `date_diff` is
# ibis `a.delta(b)`, which returns `a - b`. The arguments swap as well as move.
DATE_DIFF_UNITS = frozenset({"year", "quarter", "month", "week", "day"})
TIME_DIFF_UNITS = frozenset({"hour", "minute", "second", "millisecond", "microsecond", "nanosecond"})

# v2 `date_format(column, name)` takes a granularity name, not a format string. Names
# that bucket a timestamp to the start of a period become a v3 period-start function.
GRANULARITY_STARTS = {
    "Week": "week_start",
    "Month": "month_start",
    "Mon": "month_start",
    "Quarter": "quarter_start",
    "Year": "year_start",
}

# The rest of the buckets have no v3 period-start function. v2 returned a formatted
# string for these, so `format_date` reproduces it exactly - after translating MySQL
# DATE_FORMAT specifiers to the strftime ones v3 passes to ibis (`%i` -> `%M`).
GRANULARITY_FORMATS = {
    "Minute": "%Y-%m-%d %H:%M",
    "Hour": "%Y-%m-%d %H:00",
    "Day": "%Y-%m-%d 00:00",
    "Day Short": "%Y-%m-%d 00:00",
}

# Granularity names that extract a component rather than bucket a period.
GRANULARITY_PARTS = {
    "Minute of Hour": "minute",
    "Hour of Day": "hour",
    "Day of Week": "day_of_week",
    "Day of Month": "day",
    "Day of Year": "day_of_year",
    "Month of Year": "month",
    "Quarter of Year": "quarter",
}

# No v3 counterpart, and no per-column fallback either: their SQL contains a subquery,
# which `sql_column` rejects. The query drops to the whole-query compiled SQL instead.
BLOCKING_FUNCTIONS = frozenset({"descendants", "descendants_and_self"})

# A column bound by bare name loses to a function of the same name, because v3 binds
# the functions last. Anything here is reached through `q[...]` instead.
V3_FUNCTION_NAMES = frozenset(
    DIRECT_FUNCTIONS
    | set(RENAMED_FUNCTIONS.values())
    | set(GRANULARITY_STARTS.values())
    | set(GRANULARITY_PARTS.values())
    | {
        "asc",
        "cases",
        "constant",
        "create_buckets",
        "date_add",
        "date_diff",
        "date_sub",
        "desc",
        "ends_with",
        "filter_first_row",
        "find",
        "fiscal_year_start",
        "format_date",
        "get_retention_data",
        "group_concat",
        "if_else",
        "is_first_row",
        "is_last_row",
        "is_not_between",
        "json_extract",
        "length",
        "literal",
        "median",
        "microsecond",
        "next_period_value",
        "next_value",
        "normalize_json",
        "one_if",
        "pad_number",
        "percentage_change",
        "previous_period_value",
        "previous_value",
        "row_number",
        "second",
        "sql",
        "starts_with",
        "textsplit",
        "time_diff",
        "to_inr",
        "to_usd",
        "week_of_year",
        "year",
        "q",
    }
)

BINARY_OPERATORS = {
    "+": "+",
    "-": "-",
    "*": "*",
    "/": "/",
    "=": "==",
    "!=": "!=",
    "<": "<",
    ">": ">",
    "<=": "<=",
    ">=": ">=",
    "&&": "&",
    "||": "|",
}

LOGICAL_OPERATORS = {"&&": "&", "||": "|"}


class TranslationError(Exception):
    """This module is missing a mapping. Not the input's fault - ours."""


class Outcome(str, Enum):
    """How the caller should migrate the expression."""

    TRANSLATED = "translated"
    """A v3 expression that stands on its own."""

    FRAGMENT = "fragment"
    """A v3 expression, once each fragment is materialised by a `sql_column` operation."""

    COMPILED_SQL = "compiled_sql"
    """Not expressible at query level. Fall back to the whole-query compiled SQL."""

    BROKEN_IN_V2 = "broken_in_v2"
    """The expression did not run in v2 either. Nothing to migrate, and the compiled
    SQL cannot rescue it, because v2 never generated any. Report it and move on."""


# Which outcome wins when one expression collects several. A migration that cannot
# happen outranks one that has to fall back.
_OUTCOME_RANK = {Outcome.COMPILED_SQL: 1, Outcome.BROKEN_IN_V2: 2}


@dataclass(frozen=True)
class Blocker:
    """Something that stopped the expression, phrased for a migration report."""

    function: str
    reason: str
    outcome: Outcome = Outcome.COMPILED_SQL
    """Which outcome this blocker forces."""


@dataclass(frozen=True)
class Fragment:
    """A raw SQL column the caller must materialise before the expression can run."""

    name: str
    """Bare column name the translated expression refers to."""

    sql: str
    """SQL with table qualifiers stripped, ready for a `sql_column` operation."""

    source: str
    """The SQL as v2 wrote it, before stripping."""

    label: str | None = None
    """The alias v2 wrote after the expression, if any. `sql_column` names the column
    itself, so the alias is lifted out rather than left where it would be a syntax
    error, and it is the label the user already recognises."""

    tables: tuple[str, ...] = ()
    """Tables the source qualified its columns against."""

    columns: tuple[str, ...] = ()
    """Bare columns the stripped SQL now reads from the surrounding query."""

    ambiguous_columns: tuple[str, ...] = ()
    """Columns more than one joined table provides. Stripping guessed; check these."""

    @property
    def is_ambiguous(self) -> bool:
        """True when stripping the qualifier could have pointed at the wrong column."""
        return bool(self.ambiguous_columns) or len(self.tables) > 1


@dataclass(frozen=True)
class Translation:
    """A v3 expression, the fragments it depends on, and anything that blocked it."""

    expression: str | None
    fragments: tuple[Fragment, ...] = ()
    blockers: tuple[Blocker, ...] = ()

    @property
    def outcome(self) -> Outcome:
        if self.blockers:
            return max((blocker.outcome for blocker in self.blockers), key=_OUTCOME_RANK.get)
        if self.fragments:
            return Outcome.FRAGMENT
        return Outcome.TRANSLATED

    @property
    def is_ambiguous(self) -> bool:
        return any(fragment.is_ambiguous for fragment in self.fragments)


def translate(ast, *, table_columns=None, fragment_prefix="sql_column") -> Translation:
    """Turn a v2 expression AST into a v3 expression string.

    `table_columns` maps each table the query reads to its column names. It is only
    used to detect a name two tables share, which makes qualifier stripping a guess.

    A blocked expression comes back with `expression` set to None. The walk still
    finishes, so every blocker in the tree is reported at once rather than the first.
    """
    state = _State(table_columns=table_columns or {}, fragment_prefix=fragment_prefix)
    expression = _walk(ast, state)
    return Translation(
        expression=None if state.blockers else expression,
        fragments=tuple(state.fragments),
        blockers=tuple(state.blockers),
    )


@dataclass
class _State:
    table_columns: dict
    fragment_prefix: str
    fragments: list = field(default_factory=list)
    blockers: list = field(default_factory=list)

    def add_fragment(self, source: str) -> str:
        name = f"{self.fragment_prefix}_{len(self.fragments) + 1}"
        body, label = split_trailing_alias(source)
        sql, tables, columns = strip_table_qualifiers(body)
        self.fragments.append(
            Fragment(
                name=name,
                sql=sql,
                source=source,
                label=label,
                tables=tables,
                columns=columns,
                ambiguous_columns=self.ambiguous(columns),
            )
        )
        return reference(name)

    def add_blocker(self, function: str, reason: str, outcome: Outcome = Outcome.COMPILED_SQL) -> str:
        self.blockers.append(Blocker(function=function, reason=reason, outcome=outcome))
        return self.blocked_reference()

    def blocked_reference(self) -> str:
        """A placeholder so the walk can finish and collect every blocker in the tree.

        It never reaches the caller: `translate` drops the expression once a blocker
        exists.
        """
        return reference(f"{self.fragment_prefix}_blocked")

    def ambiguous(self, columns) -> tuple[str, ...]:
        found = []
        for column in columns:
            owners = [t for t, cols in self.table_columns.items() if column in set(cols)]
            if len(owners) > 1:
                found.append(column)
        return tuple(found)


def reference(column: str) -> str:
    """Render a column name the way a v3 expression reaches it.

    A bare name only works while it is a Python identifier that no v3 function already
    claims. Everything else goes through `q[...]`, the subscript on the current query.
    """
    if column.isidentifier() and not column.startswith("__") and column not in V3_FUNCTION_NAMES:
        return column
    return f"q[{json.dumps(column)}]"


def _walk(node, state: _State) -> str:
    if not isinstance(node, dict):
        raise TranslationError(f"expected an AST node, got {type(node).__name__}")

    node_type = node.get("type")
    handler = _HANDLERS.get(node_type)
    if handler is None:
        raise TranslationError(f"unknown node type: {node_type!r}")
    return handler(node, state)


def _column(node, state: _State) -> str:
    value = node.get("value")
    if not isinstance(value, dict) or not value.get("column"):
        raise TranslationError(f"Column node without a column: {value!r}")
    return reference(value["column"])


def _string(node, state: _State) -> str:
    return json.dumps(node.get("value"))


def _number(node, state: _State) -> str:
    value = node.get("value")
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise TranslationError(f"Number node with a non-number value: {value!r}")
    return repr(value)


def _binary(node, state: _State) -> str:
    operator = node.get("operator")
    if operator not in BINARY_OPERATORS:
        raise TranslationError(f"unknown binary operator: {operator!r}")
    left = _walk(node.get("left"), state)
    right = _walk(node.get("right"), state)
    # ibis binds `&` and `|` tighter than a comparison, so every binary node is wrapped.
    return f"({left} {BINARY_OPERATORS[operator]} {right})"


def _logical(node, state: _State) -> str:
    operator = node.get("operator")
    if operator not in LOGICAL_OPERATORS:
        raise TranslationError(f"unknown logical operator: {operator!r}")
    conditions = node.get("conditions") or []
    if not conditions:
        raise TranslationError("LogicalExpression without conditions")
    joined = f" {LOGICAL_OPERATORS[operator]} ".join(_walk(c, state) for c in conditions)
    return f"({joined})"


def _call(node, state: _State) -> str:
    name = node.get("function")
    arguments = node.get("arguments") or []

    if name == "sql":
        return state.add_fragment(_literal(arguments, 0, name))
    if name in BLOCKING_FUNCTIONS:
        return _blocked_call(name, arguments, state)
    if name == "time_elapsed":
        return _time_elapsed(arguments, state)
    if name == "date_format":
        return _date_format(arguments, state)
    if name == "between":
        return _between(arguments, state)

    v3_name = RENAMED_FUNCTIONS.get(name, name)
    if v3_name not in DIRECT_FUNCTIONS and name not in RENAMED_FUNCTIONS:
        raise TranslationError(f"no v3 counterpart for function: {name!r}")

    rendered = ", ".join(_walk(argument, state) for argument in arguments)
    return f"{v3_name}({rendered})"


def _blocked_call(name, arguments, state: _State) -> str:
    """descendants(root, tree, field) reads a nested set, which needs a subquery."""
    if len(arguments) != 3:
        raise TranslationError(f"{name} expects 3 arguments, got {len(arguments)}")
    root = _literal(arguments, 0, name)
    tree = _literal(arguments, 1, name)
    # Walk the third argument anyway, so a blocker nested under it is also reported.
    _walk(arguments[2], state)
    return state.add_blocker(
        name,
        f"reads the {tree} nested set for {root!r}, which needs a subquery that " f"sql_column rejects",
    )


def _time_elapsed(arguments, state: _State) -> str:
    if len(arguments) != 3:
        raise TranslationError(f"time_elapsed expects 3 arguments, got {len(arguments)}")
    unit = _literal(arguments, 0, "time_elapsed").lower()

    # v2 returned `b - a`; v3 returns `a - b`. The arguments swap to keep the sign.
    start = _walk(arguments[1], state)
    end = _walk(arguments[2], state)

    if unit in DATE_DIFF_UNITS:
        v3_name = "date_diff"
    elif unit in TIME_DIFF_UNITS:
        v3_name = "time_diff"
    else:
        # v2 checked the unit against its own list and raised, so this never ran
        return state.add_blocker(
            "time_elapsed",
            f"the unit {unit!r} is not one v2 accepted, so this expression raised "
            f"'Invalid unit' whenever the query ran",
            outcome=Outcome.BROKEN_IN_V2,
        )

    return f"{v3_name}({end}, {start}, {json.dumps(unit)})"


def _between(arguments, state: _State) -> str:
    """v2 `between` is date-only and widens its end bound to the end of that day.

    `add_start_and_end_time` calls `getdate()` on both bounds with no type check, so a
    bound that is not a date was never compared - `getdate(5)` returns None and the
    `strftime` that follows raises. Emitting a plain `is_between` would invent a
    comparison v2 never made, so a bad bound is reported as broken instead.
    """
    if len(arguments) != 3:
        raise TranslationError(f"between expects 3 arguments, got {len(arguments)}")
    column = _walk(arguments[0], state)
    start = _day_bound(arguments[1], "start", state)
    end = _day_bound(arguments[2], "end", state)
    if start is None or end is None:
        return state.blocked_reference()
    # v2 emitted these two literals; the end of the day is what makes the range inclusive
    return f"is_between({column}, {json.dumps(start + ' 00:00:00')}, {json.dumps(end + ' 23:59:59')})"


def _day_bound(node, position: str, state: _State) -> str | None:
    """Reduce a bound to its date the way v2's `getdate()` did, or report it broken."""
    value = node.get("value") if isinstance(node, dict) else None
    if isinstance(node, dict) and node.get("type") == "String":
        for parse in (datetime.fromisoformat, lambda v: datetime.strptime(v, "%Y-%m-%d")):
            try:
                return parse(str(value)).date().isoformat()
            except ValueError:
                continue

    described = (
        repr(value)
        if isinstance(node, dict) and node.get("type") in ("String", "Number")
        else f"a {node.get('type') if isinstance(node, dict) else type(node).__name__}"
    )
    state.add_blocker(
        "between",
        f"the {position} bound is {described}, not a date. v2 ran every bound through "
        f"getdate(), which returns nothing for a non-date, so this expression failed "
        f"whenever the query ran",
        outcome=Outcome.BROKEN_IN_V2,
    )
    return None


def _date_format(arguments, state: _State) -> str:
    if len(arguments) != 2:
        raise TranslationError(f"date_format expects 2 arguments, got {len(arguments)}")
    column = _walk(arguments[0], state)
    granularity = _literal(arguments, 1, "date_format")

    if granularity in GRANULARITY_STARTS:
        return f"{GRANULARITY_STARTS[granularity]}({column})"
    if granularity in GRANULARITY_PARTS:
        return f"{GRANULARITY_PARTS[granularity]}({column})"
    if granularity in GRANULARITY_FORMATS:
        return f"format_date({column}, {json.dumps(GRANULARITY_FORMATS[granularity])})"
    raise TranslationError(f"unknown date_format granularity: {granularity!r}")


def _literal(arguments, index, function) -> str:
    node = arguments[index] if index < len(arguments) else None
    if not isinstance(node, dict) or node.get("type") != "String":
        raise TranslationError(f"{function} expects a literal string at position {index}")
    return str(node.get("value"))


_HANDLERS = {
    "Column": _column,
    "String": _string,
    "Number": _number,
    "BinaryExpression": _binary,
    "LogicalExpression": _logical,
    "CallExpression": _call,
}


_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z_0-9$]*")

_TRAILING_ALIAS = re.compile(
    r"\s+AS\s+(?:`(?P<backtick>[^`]+)`|'(?P<single>[^']+)'|\"(?P<double>[^\"]+)\""
    r"|(?P<bare>[A-Za-z_][A-Za-z_0-9$]*))\s*$",
    flags=re.IGNORECASE,
)


def split_trailing_alias(sql: str) -> tuple[str, str | None]:
    """Separate a trailing `AS <name>` from a SQL fragment.

    A v2 `sql()` body is a whole select-list item, so users wrote the column name into
    it. `sql_column` supplies the name itself and appends its own alias, so a second one
    left in place is a syntax error. The alias is still the label the user knows, so it
    comes back rather than being dropped.
    """
    match = _TRAILING_ALIAS.search(sql)
    if not match:
        return sql.strip(), None
    body = sql[: match.start()]
    # `cast(x AS INT)` also ends in AS <word>. An alias only closes a complete
    # expression, so the text before it has to have balanced parentheses.
    if body.count("(") != body.count(")"):
        return sql.strip(), None
    alias = next(value for value in match.groupdict().values() if value is not None)
    return body.strip(), alias


def strip_table_qualifiers(sql: str) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
    """Drop the table from every qualified column reference in a SQL fragment.

    Returns the rewritten SQL, the tables it was qualified against, and the bare
    columns it now reads. A fragment runs inside a CTE over the query's own result,
    where the original table name is out of scope, so the qualifier has to go.
    """
    tokens = _tokenize(sql)
    output = []
    tables = []
    columns = []

    index = 0
    while index < len(tokens):
        qualified = _match_qualified(tokens, index)
        if qualified is None:
            kind, text = tokens[index]
            output.append(f"`{text}`" if kind == "quoted" else text)
            index += 1
            continue
        table, column, index = qualified
        tables.append(table)
        columns.append(column)
        output.append(f"`{column}`")

    return "".join(output), tuple(dict.fromkeys(tables)), tuple(dict.fromkeys(columns))


def _match_qualified(tokens, index):
    """Match `table` `.` `column` at index, tolerating whitespace around the dot.

    The match has to start at `index` exactly. Skipping leading whitespace here would
    swallow it, and `EXTRACT(HOUR FROM `t`.`c`)` would lose the space after FROM.
    """
    first = index
    if tokens[first][0] not in ("quoted", "word"):
        return None
    dot = _next_significant(tokens, first + 1)
    if dot is None or tokens[dot] != ("other", "."):
        return None
    second = _next_significant(tokens, dot + 1)
    if second is None or tokens[second][0] not in ("quoted", "word"):
        return None
    return tokens[first][1], tokens[second][1], second + 1


def _next_significant(tokens, index):
    while index < len(tokens) and tokens[index][0] == "other" and tokens[index][1].isspace():
        index += 1
    return index if index < len(tokens) else None


def _tokenize(sql: str) -> list[tuple[str, str]]:
    """Split SQL into quoted identifiers, string literals, words and single characters.

    Only enough of a lexer to tell a qualified column apart from a dot inside a string
    literal, such as the `%Y-%m-%d` argument of `strftime`.
    """
    tokens: list[tuple[str, str]] = []
    index, length = 0, len(sql)
    while index < length:
        char = sql[index]
        if char == "`":
            end = sql.find("`", index + 1)
            if end == -1:
                tokens.append(("other", sql[index:]))
                break
            tokens.append(("quoted", sql[index + 1 : end]))
            index = end + 1
            continue
        if char in "'\"":
            end = index + 1
            while end < length:
                if sql[end] == "\\":
                    end += 2
                    continue
                if sql[end] == char:
                    if end + 1 < length and sql[end + 1] == char:
                        end += 2
                        continue
                    break
                end += 1
            tokens.append(("string", sql[index : min(end + 1, length)]))
            index = end + 1
            continue
        match = _IDENTIFIER.match(sql, index)
        if match:
            tokens.append(("word", match.group(0)))
            index = match.end()
            continue
        tokens.append(("other", char))
        index += 1
    return tokens
