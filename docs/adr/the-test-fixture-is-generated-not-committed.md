# The test fixture is generated, not committed

Date: 2026-08-27

## Status

Accepted.

## Context

`insights/setup/insights_demo_data.duckdb` was a 2.3 MB DuckDB file tracked in
git.
`insights/setup/demo.py` copied it whenever `frappe.flags.in_test` or `CI` was
set, so it was the dataset every test ran against.

It was built by trimming each table of the production dataset to 100 rows,
independently. That destroyed referential integrity. Every declared join matched
**zero** rows — `orders` to `orderitems`, `orders` to `customers`, `orderitems`
to `products`, `orders` to `orderpayments`.

The damage reached the shipped content. `sample_workbook.json` holds a query
that left-joins `orders` to `orderitems` and computes `price * freight_value`.
Under `CI` it returned 2 rows with `price` entirely null, and its four charts
drew nothing.

Nobody noticed for as long as the file existed. A binary does not appear in a
diff, so no review could have caught it.

## Decision

`insights/setup/demo_data/` holds a declarative spec — tables, columns, types,
foreign keys, cardinalities, date ranges, category sets — and a seeded generator
that turns it into DuckDB at test time. The `.duckdb` file is not tracked.

Generation fails if any declared foreign key matches no rows. That check is the
point: it makes the fault that hid here impossible to reintroduce quietly.

The data is **synthesised**, not sampled from the production dataset.

## Consequences

A spec is reviewable. The dead joins were invisible for as long as the fixture
was a binary, and would be visible as a diff now.

Extending the fixture is an edit to a table definition. A new chart type needs a
new data shape — a funnel needs stages, a Sankey needs flows — and a spec grows
to fit. This was the deciding argument.

Generation costs 600 ms for 2000 orders and 4881 line items, so nothing caches
it and nothing needs to.

The accepted cost is realism. Sampling the production dataset coherently — pick
N orders, then cascade to their related rows — gives better distributions. It
was rejected because extending it requires the source to already hold the shape
needed, and for a funnel or a geographic hierarchy it does not.

Output is not byte-reproducible. DuckDB writes its own storage metadata, so the
same spec and seed give three different file hashes. The guarantee is a
row-content fingerprint. Byte identity bought nothing once the file left git.

## Where this is going

`demo.py` still downloads the production dataset from a hardcoded Google Drive
link for a real install. The same generator could replace that and make demo
setup offline and instant. It is deliberately untouched: demo data is a
first-impression surface where synthetic distributions cost something real. The
generator runs outside a test context, so that route stays open.
