# Document concurrency — decision map

Two people with the same chart open overwrite each other silently. This map records how a second editor stops being invisible.

Tickets live in `issues/`, one body of work each. A ticket carries a `Type:`, a `Status:`, and any `Blocked by:` tickets.

Written 2026-09-03, out of the chart-refresh work on `feat/charts-extract`.

## Destination

A write that has not seen the current version is refused, not applied. An editor who is not writing follows along. An editor who is about to collide can see the other person first.

No merging. The single-author assumption stays. What changes is that a loss is visible and recoverable.

## Notes

- The store is `frontend/src2/helpers/resource.ts`. Charts, queries, dashboards and workbooks all use it, so all four move together.
- This effort has no branch of its own yet. It is written on `feat/charts-extract`, and effort docs are removed when their branch merges — move it before that happens.

## Decisions so far

- **A write's answer confirms the write; it does not report other changes.** `mergeWriteAnswer` takes a field from the answer only where the answer differs from what was sent. Landed in `f39de6c9d`, before this map was written. It is what makes a silent reload safe: a document that reloads itself no longer looks edited.
