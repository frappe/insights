# 15 — Build the fixture generator

Type: task
Status: open
Blocked by: 04

## Question

Build the spec-driven fixture generator that ticket 04 decided on.

Deliver:

- A **declarative spec** in the repo: tables, columns, types, foreign keys,
  cardinalities, date ranges, category sets. Readable in a diff.
- A **generator** that turns the spec into DuckDB with a fixed seed. Same spec
  gives the same bytes every run.
- **Referential integrity by construction.** Every declared foreign key joins.
  Add a self-check that fails generation if any declared join matches zero rows —
  that is the bug this ticket exists to prevent from returning.
- A CI step that generates before the suite runs. Measured at 17 ms, so it needs
  no caching.
- **Remove `insights/setup/insights_demo_data.duckdb` from git**, and repoint the
  `frappe.flags.in_test or CI` branch in `insights/setup/demo.py` at the
  generator.

Cover enough shape for the tier A and B flows in the inventory: dates spanning at
least 18 months, at least 4 categorical values on a status column, joinable
customer, order, line-item and product tables, and a numeric measure worth
summing.

**Fix `sample_workbook.json` too.** Its query left-joins `orders` to `orderitems`
and computes `price * freight_value`. Confirm its charts render non-empty against
the generated data. It is the vehicle for every verify flow in ticket 02.

Two constraints:

- Keep the generator usable outside tests. It is scoped here as a development
  tool, but it should not need a test context to run. See the map's Out of scope
  note on the demo download.
- Do not reach for the real Olist dataset. Ticket 04 rejected subsampling.
