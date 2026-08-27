# 12 — Flows: Workbook lifecycle and navigation

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

`frontend/e2e/tests/workbook.spec.ts` holds seven flows. Each one ran five times
green, and the folder flow ran ten times.

### Covered

| # | Test title | Kind |
|---|---|---|
| W1 | a user creates a workbook from the list | author |
| W2 | a user opens a workbook and switches query, chart, dashboard tabs | verify |
| W3 | a user renames a workbook | author |
| W4 | a workbook saves and survives a reload | author |
| W5 | a user deletes a workbook | author |
| W6 | a user creates a folder and moves a query into it | author |
| W7 | a user shares a workbook with another user | author |

### Skipped

**W8, a user opens a workbook template and it materializes.** Every shipped
template declares `required_apps: ["erpnext"]`, and `test.insights.localhost`
runs `frappe` and `insights` only. `get_workbook_templates` returns an empty
list there, so the Library button never renders and the flow has no entry point.
The flow needs ERPNext on the test site. It is otherwise ready to write.

**W9 and W10** are tier C and out of this ticket.

### The W6 title differs from the inventory

The inventory reads "a user creates a folder and moves a workbook into it". The
product has no folder that holds a workbook. A folder lives inside one workbook
and holds its queries or its charts, through
`insights.api.workbooks.create_folder`. The test records what the product does,
so its title names a query. Ticket 08 will read the new sentence.

### Fixtures

None added. The ladder covered every flow. W1 and W5 create through the UI, and
both hand cleanup to the `workbook` fixture or to `deleteWorkbook`.

### Findings

**The Share button is the save indicator.** `WorkbookNavbarActions.vue` hides it
while `workbook.isdirty`, so its return is the only thing on screen that says a
change reached the server. The suite reads it that way in `expectSaved`. Without
it a test races the 1500 ms autosave debounce and reloads before the write.

**The workbook actions menu has no accessible name.** The `more-horizontal`
Dropdown in `WorkbookNavbarActions.vue` passes no label, so W5 reaches it
through `button[aria-haspopup="menu"]`. A `:label` on that Button would remove
the last CSS locator in this file.

**The workbook title is a `ContentEditable`.** Chromium exposes it as plain
text, not as a textbox, so no rung of the locator ladder reaches it. W3 and W4
use `.contenteditable` inside the navbar.

**A dashboard drops chart category labels.** The same Bar chart renders
`delivered` on the chart tab and drops it on the dashboard, because echarts
thins labels that no longer fit. Assert a value axis tick there instead.

**A parallel setup run logs the viewer out.** `ensureInsightsUser` writes
`new_password` on every setup run, and Frappe clears that user's sessions on a
password change. Two suites running at once therefore invalidate each other's
saved viewer state, and `viewerPage` lands on the login page. W7 failed twice
this way while other agents ran, and passed on every run that held the site
alone. CI runs one suite, so the gate is safe. Worth setting the password only
when the user is created.

No product bug found. No file outside `frontend/e2e/tests/workbook.spec.ts` was
changed.
