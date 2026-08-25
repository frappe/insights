# The cleanup deletes only what it can rebuild

Date: 2026-08-13

## Status

Accepted. Interim — see "Where this is going".

## Context

The weekly cleanup dropped any DuckDB table that no `Insights Table v3` row
claimed with `stored = 1`. Two paths write tables and only `WarehouseTableImporter`
set the flag. `WarehouseTableWriter`, which every `Insights Table Import Job`
writes through, set nothing. A job's table was therefore an orphan by the
cleanup's own definition.

One production job had run daily since January and kept only the days since the
last Sunday. Every import log said `Completed` (frappe/insights#1295). The
record did not survive either: `frappe.logger()` writes to `logs/frappe.log`,
which rotates.

## Decision

**A drop must be reversible. The sweep deletes nothing it cannot show to be
rebuildable.** A table is dropped when one of these holds:

- A doc says a source sync can re-import it. These are the tables
  `prune_unused_tables` un-stored, read back from the docs so a run that died
  mid-sweep still finishes next week.
- A live or re-importable table replaced it. This covers the flat
  `main."<source>.<table>"` copies left by the move to one schema per source.
- It holds no rows.

The sweep keeps everything else and reports it through `Error Log`. A row count
that fails reads as "not empty".

Two supporting choices:

- **Import job tables are named in the expected set**, read from the source's
  `schema` field and the job's `table_name` — the two values `TableWriter` hands
  to DuckDB. This is scaffolding around a write path we intend to remove, not a
  rule. It exists so a case we already understand raises no alarm.
- **`Error Log`, not a new doctype.** It is durable, filterable and has
  retention. The gap in #1295 was that the file log rotated.

Rejected: teach `WarehouseTableWriter` to claim its table and add a
`write_path_owner` field naming which writer maintains it. That fixes the writer
that forgot, not the next one, and spends a schema change plus a backfill patch
on a write path we intend to delete.

## The same rule, one layer up

`JobState.set` wrote the script's cursor to the job row inside the open
transaction, and the next log line committed it. A failed DuckDB commit left the
run marked `Failed` with the cursor past rows nothing wrote, so the next run
skipped the day.

`JobState` now buffers and `save()` runs after `_commit_table` returns. A run
that writes no rows reports `Success (No Rows)` — a transient empty response and
an empty day are indistinguishable from here.

## Consequences

**Some tables need a person.** A deleted data source leaves tables nobody
claims. The sweep keeps and reports them every week until someone acts. The
right fix is to drop a source's store copy when the source is deleted, at the
moment of the act.

**The alarm has to stay meaningful.** If unexplained orphans become routine, the
`Error Log` becomes noise and this guard buys nothing. Anything that writes Data
Store tables must claim them or be named the way import jobs are here.

## Where this is going

The durable fix is that no writer puts rows into the Data Store that exist
nowhere else.

An import job should write to a doctype, and the ordinary source sync should
copy that into the store. The store returns to being a pure cache, every table
becomes rebuildable, and this question disappears — no owner field, no exception
list, no alarm. `Insights Table Import Job` is then a scheduled Server Script,
which needs nothing from Insights.

One question stays open, which is why this ADR is interim. A log-shaped doctype
eventually gets a retention policy, and truncating it makes the store the only
copy again. The answer is an immutable archive — closed, date-partitioned
Parquet as the system of record, the store derived from it, and source retention
driven by the archive's watermark rather than a calendar. That also fixes a
measured problem: an open 41 GB `.duckdb` file cannot be backed up reliably,
while a closed Parquet partition can. See frappe/insights#1256.
