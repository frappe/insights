# 14 — Flows: Permissions in the UI

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

`frontend/e2e/tests/permissions.spec.ts` covers P1 to P4 of the "Permissions and
teams" table. All four passed three consecutive runs, with no retries and no
quarantine.

### Flows covered

| # | Title | Kind |
|---|---|---|
| P1 | a viewer sees only the workbooks granted to them | verify |
| P2 | a viewer cannot edit a workbook they can read | verify |
| P3 | an admin creates a team and grants a resource | author |
| P4 | a user without data source access cannot query it | verify |

Nothing was skipped. The table holds four flows and the file holds four tests.

### Security finding

None. Every rule the interface was asked to honour, it honoured.

Two interface warts are worth a separate ticket, but neither lets a reader write.
The backend refuses the write and the client turns auto-save off, so both are
dead controls and not holes.

1. `frontend/src2/dashboard/DashboardBuilder.vue` hides Share on `read_only` but
   still draws Edit. A reader can enter edit mode on a dashboard they may only
   read.
2. `frontend/src2/workbook/WorkbookNavbar.vue` leaves the title editable for a
   reader. The typed title is discarded without a message.

### Fixtures and helpers added

No new fixture. `viewerApi` was not needed, because the viewer acts through
`viewerPage` and every grant is an admin write.

Three functions were appended to `frontend/e2e/helpers/insights.ts`, and
`DOCTYPE.SETTINGS` was added beside the others.

- `shareWorkbook` — a grant is a DocShare row, so a REST write cannot make one.
  It calls `insights.api.workbooks.update_share_permissions`, the route the
  share dialog uses.
- `setTeamPermissions` — flips `Insights Settings.enable_permissions`. Every
  Insights User reaches every Data Source while it is off, so P4 has nothing to
  deny without it.
- `deleteTeam` — teardown for the team P3 builds through the interface.

### What the run showed

- P4 is the only test that writes a site-wide setting. It reads the stored value
  first and restores it in a `finally`, so a failure cannot leave the site
  switched. Blast radius was checked: an admin bypasses every team rule, and
  public content runs as its `permission_user`, so no other area's tests see the
  window.
- P1 cannot assert on a list count, because other agents seed workbooks into the
  same site. Both of its workbooks carry one marker, the list search narrows to
  that pair, and the assertions name the two titles.
- frappe-ui `TabButtons` renders a **radio group**, not buttons. Reach a tab with
  `getByRole('radio', { name })`.
- A frappe-ui `Tooltip` renders its text **twice** — the visible bubble, and an
  aria-hidden mirror that names the trigger. Neither carries a role that tells
  them apart, so the visible one needs `.first()`. This is the file's one lint
  warning.
- The team resource rows carry `data-source="<name>"`. That attribute is the only
  thing that names one row, because the Data Source title repeats elsewhere.
