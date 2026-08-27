# 19 — Flows: Data Source and Data Store

Type: task
Status: resolved
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

## Answer

Four flows are covered in `frontend/e2e/tests/data-source.spec.ts`, in one
`data-source` describe block. DS5 stays open, as the brief scoped it out.

| # | Flow | Shape |
| --- | --- | --- |
| DS1 | a user browses a data source's table list and previews a table | verify |
| DS2 | a user uploads a CSV and it becomes a queryable table | author |
| DS3 | a user connects a new database and the connection test reports | author |
| DS4 | a user imports a table into the data store | author |

DS1 reads the demo Data Source. It asserts four table names, opens `sellers`,
and asserts the header cell, a row value and the 60 rows the table holds.

DS2 uploads a three row CSV through the upload dialog. It asserts the preview
rows, the import toast, and then starts a query from the new table in the query
builder. The 3 rows in the result prove the table is queryable.

### What DS3 connects to

DS3 opens the MariaDB dialog and points it at `127.0.0.1:3999`. Nothing listens
on that port, so the connection test fails at once and never leaves the machine.

Two alternatives were rejected. A real remote database needs a second service in
CI. The site's own MariaDB needs the site password, which the suite has no route
to read, and repeated bad logins can make MariaDB block the host that the site
itself connects from.

DS3 asserts the report and its consequences. The Connect button turns into
`Failed, Retry?`, an error toast appears, and `Add Data Source` stays disabled.
The flow then closes the dialog and asserts the list holds no data source with
that title. Nothing is created, so DS3 needs no teardown.

### How DS4 handles the background job

`import_table` enqueues a Table Import on the `long` queue and returns at once.
The flow therefore reloads the Data Store screen until the row appears, inside
`expect(...).toPass()`. No sleep is used. The window is 150 seconds and the test
timeout is 180 seconds.

DS4 seeds its own table over REST, as a CSV in the Uploads Data Source. The
demo Data Source is untouched by every flow in the file.

**One bench worker serves `short`, `default` and `long`, in that order.** The
suite's own teardown fills `default`, so a Table Import waits for that backlog
to drain. This bench held about 1,500 stale cleanup jobs, and DS4 could not
complete at all until a worker reached `long`. It was measured with a second
worker started for that one queue:

```sh
OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES NO_PROXY='*' \
  wt run insights-e2e-tests -- worker --queue long
```

That worker is still running, with its log in `/tmp/e2e-long-worker.log`. Stop
it with `pkill -f "worker --queue long"`. **CI needs the same capacity.** A run
that serves `long` only after `default` empties will lose DS4. Without the
environment variable the work horse crashes on macOS, inside the pyarrow import
after `fork`.

### Cleanup

Each upload flow takes a unique table name from `uniqueTableName`, so three
copies of the file can run at once. A fixed name was tried first and lost one
run to a second suite run on the same site.

Teardown runs in a `finally`. It drops the Data Store copy through
`clear_warehouse_data`, deletes the Table document, and deletes the File. After
the last run the site held no `e2e` Table, no `e2e` File and three Data Sources:
`demo_data`, `Site DB` and `Uploads`.

One residue has no route out. The upload writes a DuckDB table into the Uploads
database, and no interface or API drops it. Each DS2 and DS4 run leaves one
three row table there.

New helpers: `uploadFile` on the REST client, plus `UPLOADS_DATA_SOURCE`,
`tableDocName`, `uniqueTableName`, `uploadCsvTable`, `clearDataStoreTable`,
`deleteUploadedTable` and `deleteUploadedFiles` in `helpers/insights.ts`.

### Bugs found, to be filed

1. **The import row limit is dropped.** `ImportTableDialog.vue` sends
   `row_limit`, but `insights.api.data_store.import_table` takes only
   `data_source` and `table_name`. Frappe drops the extra argument, and the
   importer reads `row_limit` from the Table document instead. The field in the
   dialog changes nothing.
2. **The Data Store list does not refresh after an import.** `importTable`
   reloads `tables[data_source]`, and the list renders `tables['__all']`. The
   user sees no new row until the screen is loaded again. DS4 records this
   behaviour by reloading.

Neither was fixed. Both are characterized as they behave today.

### Runs

- `data-source.spec.ts`: 9 green runs, plus one `--repeat-each=3` run that
  passed 12 of 12. No flakes, so nothing is quarantined.
- Full suite: 2 runs, **60 passed of 60** each, at three workers. A third run
  was stopped by the coordinator's budget cut.
- `yarn lint:e2e`: 0 errors. `tsc --noEmit` over `e2e`: clean.

Two things the runs sat on top of. Another session was editing
`frontend/src2/helpers/resource.ts`, `charts.spec.ts` and `permissions.spec.ts`
in this worktree, so both full runs included that work. The flow inventory was
left alone, because the coordinator dropped `yarn flows` and `FLOWS.md` while
this ticket ran.
