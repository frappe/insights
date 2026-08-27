# 15 — Build the fixture generator

Type: task
Status: resolved
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

## Answer

Built as `insights/setup/demo_data/`, a package beside `demo.py`:

- `spec.py` — the declarative spec. A vocabulary of frozen dataclasses, then one
  `DEMO_SPEC` literal holding 8 tables, their columns, DuckDB types, foreign
  keys, cardinalities, date ranges and category sets.
- `generator.py` — the engine, the integrity check and a command line entry.
- `__main__.py` — `python -m insights.setup.demo_data <path> --report`.

**Why there.** The generator's only consumer is `demo.py`, and the map's out of
scope note points at the demo download as the next taker. Keeping the two side
by side means that later effort changes one call site. Nothing in the package
imports Frappe, so the module runs on a bare venv with `duckdb` installed.

**Why Python and not JSON or YAML.** The spec reads as data either way, but a
Python literal names each strategy as a type. A wrong argument fails at import,
not at row 40000, and an editor can jump from `Ref("customers", ...)` to the
table it points at. The engine holds no per-table knowledge.

**Measured.** 730 ms and 2.26 MB for 150 geolocations, 400 customers, 60
sellers, 120 products, 2000 orders, 4881 line items, 2974 payments and 2000
reviews. That splits into 50 ms building rows, about 450 ms writing DuckDB and
about 200 ms checking integrity. It is 40x the prototype's 17 ms, because rows
travel through parameterised `INSERT` batches rather than Arrow. Arrow cuts the
write to 76 ms but adds a second type map and a `pyarrow` import. The dataset is
built once per site, so the cost stays a non-issue and no caching was added.

**Integrity.** Every `Ref` and `ParentKey` in the spec is a declared foreign
key. `check_integrity` runs against the written file and raises `BrokenFixture`
on an empty table, a key that joins no rows, or any orphan child row. The file
is written to a temporary name and moved into place only after the check
passes, so a failure leaves nothing behind. All 8 tables and all 8 foreign keys
report 0 orphans:

```
customers.customer_zip_code_prefix -> geolocation: 400 rows, 0 orphans
sellers.seller_zip_code_prefix     -> geolocation:  60 rows, 0 orphans
orders.customer_id                 -> customers:  2000 rows, 0 orphans
orderitems.order_id                -> orders:     4881 rows, 0 orphans
orderitems.product_id              -> products:   4881 rows, 0 orphans
orderitems.seller_id               -> sellers:    4881 rows, 0 orphans
orderpayments.order_id             -> orders:     2974 rows, 0 orphans
orderreviews.order_id              -> orders:     2000 rows, 0 orphans
```

**Determinism.** One seed gives one dataset. The DuckDB file bytes are *not*
reproducible — three identical runs gave three different hashes, because DuckDB
writes its own storage metadata. Byte identity buys nothing now that the file
has left git, so `content_fingerprint` hashes the rows instead, and a test
asserts it is stable across runs.

**`sample_workbook.json` renders non-empty, unchanged.** Its query was imported
and executed through the real ibis engine against the generated data:

| | committed binary | generated |
| --- | --- | --- |
| query rows | 2 | 459 |
| rows with a `price` | 0 | 459 |
| `sum(price)` | NULL | 206624.37 |
| `sum(order_value)` | NULL | 6687240.50 |
| distinct months | 0 | 23 |
| distinct order statuses | 0 | 5 |
| product categories | 0 | 12 |

All four charts have data: the Bar chart gets 23 monthly points, the Donut 5
slices, the Number chart five non-null measures with a 23 month sparkline, and
the Table 74 cells after its `unavailable` filter. The workbook JSON was not
touched.

The shipped filter keeps only orders that are **not** delivered, so the skew had
to be set deliberately. A realistic 97% delivery rate would leave about 6 rows
per month. `ORDER_STATUS_WEIGHTS` sets 88% delivered, which puts 459 line items
across 23 months in the sample workbook. That number is a spec constant, not a
hidden assumption.

**Also changed.**

- `git rm insights/setup/insights_demo_data.duckdb`. Nothing else referenced it,
  and `MANIFEST.in` never packaged `.duckdb`.
- `demo.py` gained `use_generated_data()`, which both the `initialize` and the
  `download_demo_data` branches now call. The download path is untouched.
- `insights/tests/test_demo_data_generator.py` — 6 tests, no site needed. They
  cover seed stability, every foreign key joining, a trimmed parent failing the
  check, and the sample workbook query returning rows.

No CI step was added. `demo.py` generates the dataset whenever `in_test` or `CI`
is set, so the suite gets it from the site build it already runs.

**For the map.** Extending the spec is cheap, which settles the open question on
tier C. A Funnel needs a stage column, so that is one `Pick` with ordered
values. A Map needs geography, and `geolocation` already carries lat, lng, city
and state, joined to customers and sellers. A Sankey needs a second categorical
on the same row. None of these needs a new strategy. What the vocabulary lacks
is correlation between numbers — `orderpayments.payment_value` is drawn
independently of the line items it pays for, so any test that reconciles the two
will fail.
