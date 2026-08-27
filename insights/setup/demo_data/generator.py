# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Turns a `Spec` into a DuckDB file.

The generator needs no Frappe context. Run it from the command line with
`python -m insights.setup.demo_data.generator <path>`.

One seed gives one dataset. The DuckDB file bytes still differ between runs,
because DuckDB writes its own storage metadata, so compare the generated rows
rather than the file.
"""

import os
import random
import tempfile
from datetime import datetime, timedelta

from insights.setup.demo_data.spec import (
    DEMO_SPEC,
    After,
    Copy,
    Int,
    Key,
    MapFrom,
    Num,
    ParentKey,
    Pick,
    Ref,
    Sequence,
    Spec,
    Table,
    When,
)


class BrokenFixture(Exception):
    """Raised when the generated data fails its own integrity check."""


def generate(path, spec=DEMO_SPEC, seed=None):
    """Write the spec to a DuckDB file at `path` and return the path.

    The file is written to a temporary name and moved into place only after the
    integrity check passes, so a failure never leaves a broken fixture behind.
    """
    rows = build_rows(spec, seed if seed is not None else spec.seed)

    directory = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(directory, exist_ok=True)
    handle, staged = tempfile.mkstemp(suffix=".duckdb", dir=directory)
    os.close(handle)
    os.remove(staged)

    try:
        _write(staged, spec, rows)
        check_integrity(staged, spec)
        os.replace(staged, path)
    except BaseException:
        if os.path.exists(staged):
            os.remove(staged)
        raise

    return path


def build_rows(spec, seed):
    """Build every table as a list of dicts, in spec order."""
    _validate(spec)
    rng = random.Random(seed)
    tables = {table.name: table for table in spec.tables}
    rows = {}
    for table in spec.tables:
        rows[table.name] = _build_table(table, tables, rows, rng)
    return rows


def check_integrity(path, spec=DEMO_SPEC):
    """Join every declared foreign key and raise on a dead one.

    A committed fixture once had every join matching zero rows. This check is
    the reason that cannot happen again unnoticed.
    """
    import duckdb

    report = []
    connection = duckdb.connect(path, read_only=True)
    try:
        for table in spec.tables:
            count = connection.execute(f'select count(*) from "{table.name}"').fetchone()[0]
            if not count:
                raise BrokenFixture(f"table {table.name} is empty")
            report.append((table.name, None, count, 0))

        for child, column, parent, parent_column in foreign_keys(spec):
            matched = connection.execute(
                f'select count(*) from "{child}" c '
                f'join "{parent}" p on c."{column}" = p."{parent_column}"'
            ).fetchone()[0]
            orphans = connection.execute(
                f'select count(*) from "{child}" c '
                f'left join "{parent}" p on c."{column}" = p."{parent_column}" '
                f'where c."{column}" is not null and p."{parent_column}" is null'
            ).fetchone()[0]
            if not matched:
                raise BrokenFixture(f"{child}.{column} joins no row of {parent}.{parent_column}")
            if orphans:
                raise BrokenFixture(f"{child}.{column} has {orphans} rows with no {parent} row")
            report.append((child, f"{column} -> {parent}.{parent_column}", matched, orphans))
    finally:
        connection.close()

    return report


def foreign_keys(spec):
    """Yield every declared foreign key as (child, column, parent, parent column)."""
    for table in spec.tables:
        for column in table.columns:
            if isinstance(column.value, Ref):
                yield table.name, column.name, column.value.table, column.value.column
            elif isinstance(column.value, ParentKey):
                yield table.name, column.name, table.parent.table, table.parent.column


# --- building ---------------------------------------------------------------


def _validate(spec):
    seen_tables = set()
    for table in spec.tables:
        if (table.rows is None) == (table.parent is None):
            raise BrokenFixture(f"table {table.name} needs exactly one of rows or parent")
        if table.rows is not None and table.rows < 1:
            raise BrokenFixture(f"table {table.name} asks for {table.rows} rows")
        if table.parent and table.parent.table not in seen_tables:
            raise BrokenFixture(f"table {table.name} names an unknown parent {table.parent.table}")

        seen_columns = set()
        for column in table.columns:
            value = column.value
            if isinstance(value, Ref) and value.table not in seen_tables:
                raise BrokenFixture(f"{table.name}.{column.name} refers to an unknown table")
            if isinstance(value, MapFrom) and value.column not in seen_columns:
                raise BrokenFixture(f"{table.name}.{column.name} reads a column declared later")
            if isinstance(value, Copy) and value.via not in seen_columns:
                raise BrokenFixture(f"{table.name}.{column.name} copies through a column declared later")
            if isinstance(value, After):
                base_is_local = value.via is None
                if base_is_local and value.column not in seen_columns:
                    raise BrokenFixture(f"{table.name}.{column.name} reads a column declared later")
                if not base_is_local and value.via not in seen_columns:
                    raise BrokenFixture(f"{table.name}.{column.name} reads through a column declared later")
            seen_columns.add(column.name)
        seen_tables.add(table.name)


def _build_table(table: Table, tables, rows, rng):
    parents, positions = _parent_slots(table, rows, rng)
    built = []
    index = {}

    for offset, parent in enumerate(parents):
        row = {}
        for column in table.columns:
            row[column.name] = _value(column, table, tables, rows, index, row, parent, offset, positions, rng)
        built.append(row)

    return built


def _parent_slots(table, rows, rng):
    """Return one parent row per row to build, plus each row's rank in its group."""
    if table.parent is None:
        return [None] * table.rows, [0] * table.rows

    parents = []
    positions = []
    low, high = table.parent.per_row
    for parent in rows[table.parent.table]:
        for position in range(rng.randint(low, high)):
            parents.append(parent)
            positions.append(position)
    return parents, positions


def _value(column, table, tables, rows, index, row, parent, offset, positions, rng):
    value = column.value

    if isinstance(value, Key):
        return f"{value.prefix}{offset + 1:0{value.width}d}"

    if isinstance(value, Ref):
        return rng.choice(_values_of(rows, index, value.table, value.column))

    if isinstance(value, ParentKey):
        return parent[table.parent.column]

    if isinstance(value, Sequence):
        return value.start + positions[offset]

    if isinstance(value, Pick):
        return rng.choices(value.values, weights=value.weights)[0]

    if isinstance(value, MapFrom):
        return value.mapping[row[value.column]]

    if isinstance(value, Copy):
        source = _referenced_row(column.name, value.via, table, tables, rows, index, row)
        return source[value.column]

    if isinstance(value, Int):
        return rng.randint(value.low, value.high)

    if isinstance(value, Num):
        return round(rng.uniform(value.low, value.high), value.decimals)

    if isinstance(value, When):
        start = datetime.fromisoformat(value.start)
        end = datetime.fromisoformat(value.end)
        return start + timedelta(seconds=rng.randrange(int((end - start).total_seconds())))

    if isinstance(value, After):
        return _after(value, column, table, tables, rows, index, row, rng)

    raise BrokenFixture(f"{table.name}.{column.name} uses an unknown strategy {type(value).__name__}")


def _after(value, column, table, tables, rows, index, row, rng):
    if value.only_when:
        gate_column, allowed = value.only_when
        if row[gate_column] not in allowed:
            return None

    if value.via:
        source = _referenced_row(column.name, value.via, table, tables, rows, index, row)
        base = source[value.column]
    else:
        base = row[value.column]

    if base is None:
        return None

    return base + timedelta(hours=rng.uniform(value.min_hours, value.max_hours))


def _referenced_row(column_name, via, table, tables, rows, index, row):
    """Find the parent row that the foreign key column `via` points at."""
    link = next(c.value for c in table.columns if c.name == via)
    if isinstance(link, Ref):
        parent_table, parent_column = link.table, link.column
    elif isinstance(link, ParentKey):
        parent_table, parent_column = table.parent.table, table.parent.column
    else:
        raise BrokenFixture(f"{table.name}.{column_name} reads through {via}, which is not a foreign key")

    return _rows_by_key(rows, index, parent_table, parent_column)[row[via]]


def _values_of(rows, index, table_name, column_name):
    key = ("values", table_name, column_name)
    if key not in index:
        index[key] = [row[column_name] for row in rows[table_name]]
    return index[key]


def _rows_by_key(rows, index, table_name, column_name):
    key = ("rows", table_name, column_name)
    if key not in index:
        index[key] = {row[column_name]: row for row in rows[table_name]}
    return index[key]


# --- writing ----------------------------------------------------------------


# One INSERT per row costs about 8x one INSERT per batch, so rows travel in batches.
BATCH_SIZE = 500


def _write(path, spec: Spec, rows):
    import duckdb

    connection = duckdb.connect(path)
    try:
        for table in spec.tables:
            columns = ", ".join(f'"{c.name}" {c.type}' for c in table.columns)
            connection.execute(f'create table "{table.name}" ({columns})')
            _insert(connection, table, rows[table.name])
        connection.execute("checkpoint")
    finally:
        connection.close()


def _insert(connection, table, table_rows):
    row_placeholder = "(" + ", ".join("?" for _ in table.columns) + ")"
    for start in range(0, len(table_rows), BATCH_SIZE):
        batch = table_rows[start : start + BATCH_SIZE]
        values = []
        for row in batch:
            values.extend(row[column.name] for column in table.columns)
        placeholders = ", ".join([row_placeholder] * len(batch))
        connection.execute(f'insert into "{table.name}" values {placeholders}', values)


def main():
    import argparse
    import time

    parser = argparse.ArgumentParser(description="Generate the Insights demo dataset.")
    parser.add_argument("path", help="where to write the DuckDB file")
    parser.add_argument("--seed", type=int, default=None, help="override the spec seed")
    parser.add_argument("--report", action="store_true", help="print the integrity check")
    arguments = parser.parse_args()

    started = time.perf_counter()
    generate(arguments.path, seed=arguments.seed)
    elapsed = (time.perf_counter() - started) * 1000

    size = os.path.getsize(arguments.path) / 1024 / 1024
    print(f"wrote {arguments.path} in {elapsed:.0f} ms, {size:.2f} MB")

    if arguments.report:
        for table, key, matched, orphans in check_integrity(arguments.path):
            label = f"{table}.{key}" if key else table
            print(f"  {label}: {matched} rows, {orphans} orphans")


if __name__ == "__main__":
    main()
