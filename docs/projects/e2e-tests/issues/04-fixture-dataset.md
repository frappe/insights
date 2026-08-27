# 04 — The fixture dataset

Type: grilling
Status: open

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
