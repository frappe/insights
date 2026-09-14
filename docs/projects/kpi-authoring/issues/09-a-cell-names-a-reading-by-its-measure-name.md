# A cell names a reading by its measure name

Type: task
Status: open

## Question

A dashboard cell says which reading of a Number chart it draws with `WorkbookDashboardChart.column`, and that is the reading's `measure_name` (`frontend/src2/types/workbook.types.ts:173-181`). A measure name is the author's label: they rename it in the chart's own form and every cell that named it stops finding it.

What the reader sees is `adapter/number.ts:126` — a titled card with a dash and "Reading not found". The chart still runs, the reading still exists, and nothing in the rename said the dashboard would lose it.

Settled for now: the name is the address, and this ticket is the record of that, not a complaint about it.

## What a fix would have to answer

1. **What a reading is, apart from its name.** A measure carries no id today.
   Giving it one is a stored shape change and a migration for every chart, and
   every place that reads a reading by name — the cell, `route_filters`'
   `query::column` links, the drill's `target.column`, the pivoted column
   names a Table chart produces — would have to read the id instead or hold
   both. `docs/adr/type-independent-chart-config.md` is where the config shape
   is going, and a reading's identity belongs in that shape rather than beside
   it.

2. **Or: a rename that carries.** The chart's form knows the old name and the
   new one. Rewriting the cells that named it is a write to another document
   from a chart save, across a workbook the author may not hold write access
   on for every dashboard.

3. **Or: say so at the rename.** Cheapest of the three, and the only one with
   no stored shape in it: the form warns that N cells name this reading, and
   the author decides.

## Why it is not (3) already

Nobody has measured how often a reading is renamed after a cell names it. A warning on every rename is a cost paid by every author to protect the few, and `missing` is already a legible failure rather than a silent one. The measurement is the first step, not the warning.
