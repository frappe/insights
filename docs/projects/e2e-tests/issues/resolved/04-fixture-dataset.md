# 04 — The fixture dataset

Type: grilling
Status: resolved

## Question

What data does the suite run against?

Candidates: the demo dataset that `insights/setup/` installs, a small
purpose-built DuckDB fixture, the shipped workbook templates, or data created
per-test through `insights/tests/factories.py`.

The tension is between realism and cost. Chart and dashboard flows need enough
rows for an aggregation to be meaningful. Every row is site build time in CI,
which ticket 03 is pricing.

Decide three things:

- The dataset, and where it lives in the repo.
- Whether it is loaded once per CI run or created per test.
- Whether tests may mutate it, and if so how isolation is kept under
  `fullyParallel`.

## Answer

**The fixture is generated, not committed.**

The existing fixture is broken. `insights/setup/insights_demo_data.duckdb` is
tracked in git at 2.3 MB, and `demo.py` already copies it instead of downloading
when `frappe.flags.in_test` or `CI` is set. That looked like a free answer. It is
not: the file was trimmed to 100 rows per table independently, so referential
integrity is gone and **every join returns zero matched rows** — `orders` to
`orderitems`, `orders` to `customers`, `orderitems` to `products`, `orders` to
`orderpayments`.

The knock-on reaches the seeded content. `sample_workbook.json` holds one query
that left-joins `orders` to `orderitems` and then computes `price * freight_value`.
Under CI that query returns 2 rows with `price` entirely NULL, so its four charts
render empty. Agents writing chart assertions against this would have produced
tests that pass on nothing.

**Decision: a declarative spec plus a seeded generator.** The repo holds a
readable table spec — tables, columns, types, foreign keys, cardinalities, date
ranges, category sets. A generator turns it into DuckDB at CI time. The
`.duckdb` file leaves git.

Three reasons:

1. **A binary cannot be reviewed.** The dead joins survived because no diff ever
   showed them. A spec shows them.
2. **Generation is free.** Measured at 17 ms for 2000 orders, 4000 line items,
   400 customers and 120 products — 1.3 MB, 24 distinct months, 4 order statuses,
   every join matching. There is no cost argument for committing the output.
3. **The fixture must keep growing.** New chart types need new data shapes. A
   funnel needs stages, a Sankey needs flows, a Map needs geography. Extending a
   spec is an edit to a table definition. Extending a binary is hand-crafting a
   new one.

**Synthesize, do not subsample.** Coherently sampling the real Olist dataset —
pick N orders, cascade to related rows — gives better distributions. It is
rejected because extending it requires the source to already hold the shape
needed, and for a funnel or a geo hierarchy it does not. Seeded synthesis gives
determinism and extensibility. The accepted cost is that distributions look
manufactured.

**Loaded once per CI run, read-only.** The DuckDB file is source data. No flow
writes to it. Workbooks, queries and charts are created per test through the API,
which keeps `fullyParallel: true` safe with no reset cost between tests.

Ticket 15 builds the generator.
