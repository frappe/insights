# The schema is a coordinate, not part of a table's name

Date: 2026-09-07

## Status

Accepted. Interim — see "Where this is going".

## Context

`Insights Table v3` derives its primary key from the table it names:

```python
def autoname(self):
    self.name = get_table_name(self.data_source, self.table)   # md5(data_source + table)
```

That same string is what every referrer quotes. A query names its source as
`{data_source, table_name}` in the operations JSON. A Table Link, an
`Insights Query Reference` and an import log all name it the same way. A grant
names the derived key.

Postgres puts the schema in that string, but only when the Data Source reads
from more than one schema. `frappe/insights#1254` made it conditional to fix
`frappe/insights#1195`, where an unconditional `public.` prefix broke the table
to doctype mapping and leaked into the UI.

The condition reads the `schema` field of the Data Source. So a field a person
can edit decides how every Table under it is named. Remove one schema from that
field and every stored name is the wrong one.

The table list sync compared the remote names to the stored names as strings:

```python
new_tables = set(remote_tables) - set(existing_tables)
```

A re-named table therefore read as a table never seen. The sync created a second
record and kept the first. Both stayed `stored = 1`, so the daily Table Import
ran twice against one remote table and took the Data Store write lock twice. A
production site reported 22 such pairs out of ~84 tables
(`frappe/insights#1371`).

The duplicate is the visible cost. The design cost is larger. Seven pieces of
code exist only because the schema sits inside the name: `qualify_table_names`
decides whether to encode it, `format_table_name` encodes it,
`split_table_name` decodes it, `strip_schema_prefix` decodes it again for the
doctype mapping, `table_identity` undoes the encoding to compare,
`reconcile_table_names` finds the records the encoding stranded, and
`table_rename` rewrites six referrers when the encoding changes.

## Decision

**A Table's stored name must not encode anything that can change.**

Until the schema leaves the name, the sync holds the line. It resolves every
remote name and every stored name to the table it points at, and compares those.
On a match it renames the record. Where both names already exist it merges them,
so a site the old sync duplicated repairs itself on the next sync.

Two supporting choices:

- **A merge moves the whole record, not only its Data Store copy.** On an
  affected site the survivor is the duplicate the sync made, so the grants, the
  row restrictions and the import settings all sit on the record being folded
  in. Only `stored`, `last_synced_on` and `last_sync_bookmark` wait on the copy
  moving. A cleared `stored` re-imports on the next read. A cursor column a
  person typed does not come back.
- **A Data Store failure never aborts a rename.** The write lock is held for the
  length of a Table Import, so a drop or a rename can time out at any moment. An
  undropped table is an Unexplained Orphan, which the weekly cleanup already
  finds and reports. A half-renamed set of records is not recoverable.

Rejected: **qualify every postgres name, always.** This is the shortest route to
one name per table, and it is blocked. `insights/workbook_templates/` names 13
tables as bare `tab...` strings. So does every exported workbook, and every
template another app ships through the `insights_workbook_templates` hook. The
bare name is the portable name. Qualifying the stored name breaks all of them on
a postgres site. It also keeps the rename, because existing records still have
to move on to the qualified name.

Rejected: **let the sync delete a record it cannot match.** A re-named table then
reads as a delete and a create. The record's grants, import settings and Data
Store copy go with it. That is worse than the duplicate it fixes.

## Consequences

**A request path carries a rename engine.** Saving a Data Source can now rewrite
every query on the site. It runs only when a name actually changed, which is
rare, but the cost is there.

**`split_table_name` still guesses.** It reads the part before the first dot as
a schema when that schema is configured. A table named `v1.2 metrics` is safe. A
table literally named `sales.orders` inside `public` is not, once `sales` is
configured. This is inherited from `frappe/insights#1254` and is not widened
here. It goes away with the name.

**Stale records still survive.** A table dropped at the source leaves its record
behind forever. That gap is independent of naming and belongs to the sync.

## Where this is going

Give the schema its own field.

```
Insights Table v3
  data_source   prod_pg
  schema        public                              a coordinate, in its own column
  table         orders                              always bare
  name          md5(data_source + schema + table)
```

Two tables named `orders`, in `public` and in `sales`, are then two records with
two keys. The prefix existed only to keep those apart, and the key does that
instead. The `schema` field of the Data Source can change to anything, and no
record's name changes with it.

Six of the seven pieces go: `qualify_table_names`, `format_table_name`,
`split_table_name`'s guess, `strip_schema_prefix`, `table_identity` and
`reconcile_table_names`. `table_rename` survives as the one-shot migration, and
goes with it.

The cost is one thing, and it is the whole decision. A query names its source by
a bare `table_name`. Two records for `orders` make that ambiguous, so the
reference needs an optional `schema` key and a default for every document
written before it. The operations JSON is saved, exported and shipped in
templates, so this is a format change to a portable document.

Templates keep working through that default: a bare name resolves against the
Data Source's first schema, which is where a frappe database keeps its tables.

Pay for one format change, or keep a translation layer between two names for one
table. This ADR is interim because the first has not been paid yet.
