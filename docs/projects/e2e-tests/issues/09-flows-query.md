# 09 — Flows: Query building and operations

Type: task
Status: resolved
Blocked by: 02, 07

## Question

Cover this area's flows from the ticket 02 inventory, to the 80% bar.

Follow `frontend/tests/AGENTS.md` and pattern-match the two exemplar tests from
ticket 07. Do not invent a helper style. If a flow needs something the fixtures
do not offer, add it to the shared fixture module rather than working around it
locally.

Baseline is characterization: record what the UI does today. A test that
disagrees with the code means the test is wrong. If you find a genuine bug, file
it as a new ticket on this map and move on — never fix it here.

The answer lists the flows covered, the flows skipped and why, and any fixture
added.

## Answer

15 flows now run in `frontend/e2e/tests/query.spec.ts`. Q1 was already there, so
this ticket added 14. Two inventory flows have no route through the UI, and one
new flow replaced the closer of the two.

### Covered

| # | Test title | How it proves itself |
| --- | --- | --- |
| Q1 | a user picks a table as a query source and sees rows | 100 rows, `ORD-00001` |
| Q2 | a user adds a filter and the row count falls | 100 rows fall to 53, no `delivered` |
| Q3 | a user adds a summarize and the grain changes | 6 rows, `count_of_order_id`, `1,778` |
| Q4 | a user joins a second table and sees its columns | `customer_city` and `sao paulo` appear |
| Q5 | a user adds a mutate with an expression and sees the new column | `shout` column holds `DELIVERED` |
| Q7 | a user removes an operation mid-pipeline | 53 rows return to 100, the sort survives |
| Q8 | a user renames and removes columns | `order_status` becomes `status`, `order_approved_at` goes |
| Q9 | a user casts a column type | every time drops to `00:00:00` |
| Q10 | a user sorts by a column | first page starts at `ORD-02000` |
| Q12 | a user filters on a date with the relative date picker | `Last 1 Year` empties the table |
| Q13 | a user writes a native SQL query and runs it | 6 rows out of raw SQL |
| Q14 | a user pivots wider | 12 rows, one column per payment type |
| Q15 | a user unions two queries | 16 rows become 49, both statuses show |
| Q16 | a user opens View SQL and sees compiled SQL | the dialog shows the compiled statement |
| new | a user steps back to an earlier operation and the results rewind | 53 rows return to 100 |

### Skipped

- **Q6, a user reorders operations.** The product has no reorder. `QueryOperations.vue`
  offers click to select, double click to edit and an X to remove, and nothing
  drags. `query.ts` has no move function. This is a missing capability, not a
  defect, so no bug ticket. The new flow above covers the nearest real
  behaviour: an earlier step can be made active and the results roll back to it.
- **Q11, a user sets a limit.** The `limit` operation exists in
  `query.types.ts` and in `helpers.ts`, but `AddOperationPopover.vue` offers no
  entry for it and nothing else calls it. The flow is unreachable from the UI.

### Fixtures

None added. The tests that need a non-default table or a seeded filter call
`createQuery` from `helpers/insights.ts` directly, as `AGENTS.md` prescribes.

### Bugs found

None. Two behaviours look odd but are consistent, so they are recorded as the
baseline:

1. A cast from Datetime to Date still prints a time. The cells read
   `2018-09-12 00:00:00`, not `2018-09-12`.
2. A filter that matches nothing keeps the header row and shows an empty body.
   The "No data to display." state belongs to a result with no columns, so it
   never appears here.

### Accessible names worth adding

Four locators had to fall back to CSS because the control carries no accessible
name. Each one is a one line `:label` away from `getByRole`:

- the toolbar overflow menu in `QueryToolbar.vue`
- the column menu and the column type trigger in `QueryBuilderTable.vue`
- the X that removes an operation in `QueryOperations.vue`
- the operator select in `FilterRule.vue`, reached today through `#operator`

This ticket did not edit `frontend/src2/`.

### Runs

`yarn lint:e2e` reports no errors for this file. It reports 7
`no-nth-methods` warnings, all on positional locators that carry a reason.

Every test ran green in six full passes of the spec, three of them after the
last edit. No test was quarantined and none flaked.


### Amendment, ticket 17

Q8 became two flows, `a user renames a column` and `a user removes a column`.
The rename redraws the results twice, once when the new rows arrive and once
when the save answer replaces the document, and the removal's open column menu
closed under whichever redraw it met. Ticket 16 records the product bug. One
edit per flow, over a page that has gone quiet, has neither redraw to dodge.
