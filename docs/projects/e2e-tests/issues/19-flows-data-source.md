# 19 — Flows: Data Source and Data Store

Type: task
Status: open
Blocked by: 08

## Question

Cover the Data Source and Data Store flows. Ticket 02 put five of them in the
inventory and four inside the 80% cut. No ticket was ever written for them, so
none of the five is covered.

This is the single largest hole in the suite. It costs the effort 5 of the 68
flows, which is 7 points of coverage. Ticket 08 measured the suite at 74%, and
this area alone is the difference between that and the 80% bar.

The five flows, with their ticket 02 tiers:

| # | Flow | Tier |
|---|---|---|
| DS1 | A user browses a data source's table list and previews a table | A |
| DS2 | A user uploads a CSV and it becomes a queryable table | B |
| DS3 | A user connects a new database and the connection test reports | B |
| DS4 | A user imports a table into the Data Store | B |
| DS5 | A user removes a Data Store table | C |

Follow `frontend/e2e/AGENTS.md`. The area file is `e2e/tests/data-source.spec.ts`
and its one `test.describe` is named `data-source`. Run `yarn flows` when the
tests pass, and commit `e2e/FLOWS.md` with them.

Two things to settle while writing, because neither has a precedent in the
suite:

- **DS3 needs a second database to connect to.** Decide whether the flow can
  test the connection against the site's own MariaDB, or whether it can only
  assert that a bad connection reports a failure. A test that needs a second
  service in CI is worth avoiding.
- **DS2 and DS4 write into the shared DuckDB Data Store.** Every worker shares
  it. Give each test a unique table name and delete it in teardown, and check
  that a parallel run of DS5 cannot remove another test's table.
