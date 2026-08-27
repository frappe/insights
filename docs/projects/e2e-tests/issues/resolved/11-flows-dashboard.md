# 11 — Flows: Dashboards, filters and layout

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

`frontend/e2e/tests/dashboard.spec.ts` holds eight flows, one `test.describe`
named `dashboard`.

### Flows covered

| # | Title | Kind |
|---|---|---|
| D1 | a user creates a dashboard and adds a chart | author |
| D2 | a user adds a dashboard filter and linked charts refilter | author |
| D3 | a user moves and resizes a dashboard item | author |
| D4 | a dashboard loads with all charts rendered | verify |
| D5 | a user adds a text block | author |
| D6 | a user removes a dashboard item | author |
| D7 | a user shares a dashboard and opens the public link | author |
| D8 | a dashboard filter with no linked chart changes nothing | author |

D2 asserts the rendered chart before and after the filter. Before, the value
axis shows a `1.8K` tick, which the 1,778 delivered orders set. After, the only
category is `canceled` and the `1.8K` tick is gone.

D3 works. `grid-layout-plus` drives `interact.js`, and a stepped `page.mouse`
path moves and resizes an item reliably. The test asserts the item box grows,
then reloads the page and asserts the layout survived. No quarantine tag was
needed.

D4 seeds a second Chart over the fixture Query, so "all charts" means two.

D7 covers the authoring half only. It creates the public link and proves the
access is stored. Ticket 13 owns the logged-out view.

### Flows skipped

- **D9**, duplicate a dashboard item. Tier C, out of scope.
- **D8 was renamed.** The inventory says a filter with no linked chart "warns".
  Nothing warns. The filter saves, the value list stays empty, a typed value
  applies, and no linked chart exists to change. The test records that, and the
  title states it. See bug 3 below.

### Fixture change

`createDashboard` in `frontend/e2e/helpers/insights.ts` now seeds
`moved: false` inside every item layout. This is an addition of one key. It
matters, and bug 2 explains why.

### Bugs to file

1. **Save leaves the filter editor open.** `saveEdit` in
   `frontend/src2/dashboard/DashboardFilterEditor.vue` writes the item but never
   clears `dashboard.editingItemIndex`. The dialog stays open with Save now
   disabled, so the user must press Cancel or the close cross to leave. The Save
   action in `DashboardText.vue` clears the index, so the two editors differ.

2. **An autosave that lands during an edit drops the edit.**
   `updateDocState` in `frontend/src2/helpers/resource.ts` replaces `doc`
   wholesale, so `doc.items` becomes a new array of new objects.
   `Dashboard.isEditingItem` matches by `items.indexOf(item)`, so an open item
   editor holds an orphan, the dialog closes, and the typed values are lost.
   `VueGridLayout` triggers exactly this on every load: `grid-layout-plus`
   writes its own `moved` key into each layout, the document turns dirty, and
   the autosave fires 1.5 seconds later. A user who presses Edit inside that
   window loses the next edit. The fixture change hides the load-time case from
   the suite, and the product race remains.

3. **An unlinked dashboard filter says nothing.** The editor saves a filter
   with its Linked Charts switch off. The control then offers no values,
   because no chart names a column for it, and an applied value reaches no
   query. Nothing tells the user.

4. **Four icon-only buttons carry no accessible name.** The apply and clear
   buttons in `Filter.vue`, and the edit and delete actions in
   `DashboardItemActions.vue`. The tests reach them through a lucide class, with
   the reason on the line above. A `:label` on each would remove both CSS
   locators.

### Runs

Every test ran green at least five times after its last change. All flows except
D7 ran eight times: three sequential runs, one run with `--repeat-each=3` under
six workers, and two more sequential runs. D7 ran five times, over the last two
of those groups. `npx eslint e2e/tests/dashboard.spec.ts` reports no errors.

### Amendment, ticket 17

D2 became two flows. Bug 2 above is now ticket 16 on the map, and it costs D2
the whole editor: adding a filter starts a save, the answer replaces
`doc.items` while the editor is open, and the editor's Save then writes onto an
item the dashboard no longer holds.

- **D2** `a user adds a dashboard filter` — the editor half. **Quarantined
  2026-08-27 against ticket 16.** The editor keeps a draft and writes it onto
  the item on Save, and the save that adding the filter started replaces
  `doc.items` while the editor is open, so Save writes onto an orphan.
- **D2b** `a linked chart refilters when a dashboard filter is applied` — the
  filter is seeded, so the flow edits nothing and cannot lose an edit. It
  carries the refilter assertions D2 used to carry.

`createDashboard` takes a `filters` option for this. A filter routes through a
link string spelled `` `query`.`column` ``, keyed by the Chart it reaches.
