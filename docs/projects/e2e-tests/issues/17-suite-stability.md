# 17 — Make the suite stable enough to gate a merge

Type: task
Status: resolved
Blocked by: 09, 10, 11, 12, 13, 14

## Question

Three full-suite runs, same command, nothing changed between them, gave 54
passed, then 27 failed, then 1 failed. Each spec file was written by a different
agent, and none of them had ever run the whole suite at five workers. Find what
makes a run fail, fix it, and prove the fix over repeated full runs.

## Answer

Two causes, unrelated to each other. Neither is a bad test.

### 1. The background job queue overflows, and every write turns into a 503

**This is the mass failure.** A full run enqueues about 300 background jobs.
Most are `frappe.model.delete_doc.delete_dynamic_links`, one per document the
fixtures' Workbook deletes cascade to, and the rest are
`insights.insights.query_utils.sync_query_references`, one per Query save. One
`bench worker` drains about two a second. A run lasts 53 seconds, so the queue
grows by about 190 jobs a run and never empties between runs.

Frappe caps the queue at `max_queued_jobs`, which is 500 plus 50 per site on the
bench. Past the cap `frappe.enqueue` throws, and **every write that enqueues a
job answers 503**:

```
frappe.exceptions.QueueOverloaded: Too many queued background jobs (1150).
Please retry after some time.
```

Seeding, teardown and the app's own autosave all take that route, so the failure
lands on whichever tests happen to be running. That is why a mass failure spans
unrelated spec files, and why the next run is clean: the queue drained.

**Measured.** Five runs from an empty queue passed 53, 53, 54, 54, 53 while the
queue climbed 0 → 838. Four more runs on top of that backlog passed 54, 54, then
**37 of 54** as the queue crossed 1151, then 54 again. The failing run lost
tests in `dashboard`, `query`, `shared` and `workbook` at once, which is the
shape of the original bad run.

**Fixed** by raising the ceiling on the site, in CI and in the local
instructions, and by retrying 503 and 508 in the suite's REST client. Frappe
uses both statuses to mean "retry later". The retry covers a burst. It cannot
cover a queue that never drains, so the ceiling is the real fix.

### 2. An autosave answer drops edits made while it was in flight

The remaining failure, and the one the third run showed. Ticket 16 records it as
a product bug. The suite works around it with one rule, now in `AGENTS.md`:
never wait in the middle of an edit. Two edits of one interaction run back to
back, and an unavoidable wait goes before the first edit.

Four flows broke that rule.

| Flow | What was lost | Change |
| --- | --- | --- |
| `charts` — a user creates a Table chart | the aggregation, which tore down the column list its next click needed | the three picks now run back to back |
| `charts` — a user sorts a chart | the direction flip | split, so the flip is its own flow over a chart whose sort is seeded |
| `query` — a user renames and removes columns | the open column menu, which the redraw closed | split, one edit per flow |
| `dashboard` — a user adds a dashboard filter and linked charts refilter | the whole editor, whose Save wrote onto an orphaned item | split, so applying a filter runs over a filter the fixture seeded and edits nothing; the editor half is quarantined |

Three of the four were split rather than reordered. Reordering was tried first
on two of them and measured: grouping the edits moves the collision, it does not
remove it, because the browser can stall for longer than the debounce under five
workers. **A flow that makes one edit cannot lose it.** That is the shape to
reach for.

The splits add three flows: `a user flips a chart sort to descending`,
`a user removes a column`, and `a linked chart refilters when a dashboard filter
is applied`. Each carries the assertion its parent carried. The suite goes from
54 tests to 57.

`createDashboard` in `frontend/e2e/helpers/insights.ts` now seeds filter items.
A filter routes through a link string spelled `` `query`.`column` ``, keyed by
the Chart it reaches.

### 3. Chart pages never stop saving

Splitting and reordering still left about one chart flow failing a run, and the
flow was different each time. Reading the payloads showed why: a chart page
sends the **same** `frappe.client.set_value` about every 1.5 seconds, for as
long as it is open. Ticket 18 has the mechanism. It means ticket 16's window is
never closed on a chart page, and no ordering of clicks avoids it.

That is why the chart author flows could not be made deterministic by ordering,
and why the fix for them ended up being worker count.

### 3a. A seeded Chart was also dirty before the flow touched it

Splitting the flows was not enough. `a user adds a second measure` makes four
clicks back to back and still failed 2 runs in 6, so the save it lost was not
one of its own.

It was the load. The chart builder writes its own defaults into any config that
arrives without them, which turns the document dirty as it mounts, and the
autosave 1.5 seconds later lands in the middle of whatever the flow is clicking.
This is the same fault the dashboard fixture already worked around with
`moved: false`.

Measured, by seeding a chart, loading it, and reading the document back. A Bar
config gains exactly two keys:

```json
{ "filters": { "filters": [], "logical_operator": "And" }, "y_axis": { "stack": true } }
```

A Donut gains `filters` and `legend_position`. A Line and a Number gain nothing.

`countByConfig` and `barConfig` now seed the Bar pair, so a seeded chart is
clean the moment it loads. **Seed the defaults the builder would write.** That
is the fixture-level version of the same rule, and it fixes every flow at once
rather than one at a time.

### 4. Worker count, measured last

Worker count was checked first and cleared: before the fixture work, the Table
chart flow failed 2 of 5 runs at four workers and 3 of 10 at five. The count was
not the cause of anything, and the config was left alone.

It became the last lever once the causes were gone. Ticket 18 leaves a save in
flight on a chart page at all times, so a click is dropped whenever it lands in
one round trip, and the round trip scales with how many workers share the one
site. Measured over seven full runs each:

| Workers | Pass counts | Run time |
| --- | --- | --- |
| 5 | 56, 55, 55, 56, 55, 55, 55 | 60 s |
| 3 | 56, 56, 56, 56, 56, 56, 56 | 77 s |

At five the losses rotate: `a user adds a second measure` twice, `a user flips a
chart sort` once, `a user creates a Table chart` once, `a user drills down from
a chart` once. Every one of them is a chart author flow, which is the signature
of ticket 18 rather than of five separate faults.

**`workers` is now 3, in CI and locally.** Sixteen seconds buys the gate. Put it
back to five when ticket 18 lands.

### One test is quarantined

`dashboard` — **a user adds a dashboard filter**, tagged `@quarantine` on
2026-08-27 against ticket 16. The filter editor keeps a draft and writes it onto
the dashboard's item on Save. Adding the filter starts a save, and the answer
replaces `doc.items` while the editor is open, so Save writes onto an item the
dashboard no longer holds. Nothing the test does changes that, and it loses
about one run in five.

The refilter assertions the flow used to carry now live in
`a linked chart refilters when a dashboard filter is applied`, which seeds the
filter and is green. What quarantine costs is coverage of the editor itself.

## What else this found

- **A killed run can leave team permissions on.** `permissions.spec.ts` turns a
  site-wide setting on for one test and restores it in a `finally`. A run killed
  inside that test leaves the site in a state no later test states. The setup
  project now turns it off at the start of every run.
- **A public execution is immune to that window.** It runs as the user recorded
  at publish time, which is the admin, so `check_table_permission` lets it
  through whatever the setting says. `shared.spec.ts` needs no isolation.
