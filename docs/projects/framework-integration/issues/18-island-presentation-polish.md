# 18 — Island presentation: the full viewer UX

Type: task
Status: resolved
Blocked by: 17
Spec: [spec-insights-foundation.md](../spec-insights-foundation.md), "Island presentation and the desk-page split"

## What to build

The complete viewer-first page body from the desk dashboard page UX ticket,
rendered by the `insights.dashboard` island:

- A sticky filter bar: applied values as visible chips, per-user
  per-dashboard persistence that survives reload.
- The quiet title row completed: title, freshness stamp ("as of 9:42"),
  refresh action.
- Per-card empty-data state, with one-click filter reset when filters caused
  the empty result.
- Per-card error state: the failing card degrades in place with retry.
- The denied page state: one quiet state, identical whether the content
  exists or not, leaking no existence information.
- The rights-gated overflow menu: "Edit in Insights" opens the builder in a
  new tab and renders only when the capability flags allow it. A pure viewer
  sees exactly two affordances: filter and click-a-chart.

Chart-segment click stays reserved for the drill ticket — no drill behavior
lands here. Per-card state rendering converges to frappe-ui charts v2
primitives when the charts rewrite lands — build on what exists today
without inventing a parallel primitive.

## Acceptance criteria

- [x] Filter values apply, show as chips, persist per user per dashboard,
      and survive reload
- [x] The title row shows freshness and refresh works
- [x] An empty-because-filtered card offers one-click filter reset
- [x] A failing card shows retry in place while other cards render
- [x] Denied and missing content render the identical page state
- [x] "Edit in Insights" appears only with edit capability and opens a new
      tab; a pure viewer sees no authoring affordances

## Comments

2026-08-05 — built.

**Which cards a filter changes is now part of the answer.** `present_item` adds
`charts` to a filter item: the chart names the filter links to, and nothing
else — the column it lands on stays behind with `links`, as before. That one
field carries three things the page could not do without it: refetch only the
cards a filter reaches, let an empty card say a filter caused it, and route the
per-card filter state. The page hands each card only the filters that land on
it; a card refetches on the content of that state, not its identity, so moving
one filter leaves the other cards alone (verified: four cards, two linked, two
requests).

**Filter state is the reader's.** It is kept in the browser under
`insights:dashboard-filters:<user>:<dashboard>` — per user because a shared
workstation must not hand one person's view to the next, per dashboard docname
(not the reference the host mounted with, which may be a slug). Restored state
wins over the item's default; the mount props are the starting point under both.
Nothing on the server holds per-user view state today and a desk page has no
place to put one, so this is v1's answer, not the final one.

**The filter control is one component, not two.** `dashboard/FilterControl.vue`
came out of `DashboardFilter.vue`: the trigger, the applied label and the
popover. The builder keeps its store wiring around it, the island passes viewer
state. Applied filters read as chips — `subtle` variant with a clear affordance
— on both surfaces.

**Filter values needed an endpoint.** `get_filter_values(dashboard,
filter_name)` answers what the picker offers, looked up from the filter's name
because the link that names the column is what never crosses the boundary. It
runs under the linked chart's `data_authority`.

*Un-owned change this wants:* `Insights Query v3.get_distinct_column_values`
carries an `Insights User` role check on the method, so the viewer path calls
the undecorated function. The check belongs on the whitelist boundary, not on
the method — splitting it (a whitelisted wrapper over a plain method) also fixes
the same wall on `Insights Dashboard v3.get_distinct_column_values`, which a
guest on a public shared dashboard hits today.

**Freshness is read off the cards.** `get_chart_data` already stamps
`executed_at`; the page shows the oldest of the loaded cards, which is the
honest answer when every card fetches on its own. A cached result (10-minute
window) reports the fetch, not the age of the rows — the cache keeps no
timestamp to report. Refresh forces every card, and after it the stamp is exact.

**Table sort is gone rather than dead.** `ChartBody`/`TableChart` take
`readonly`, which is what the viewer passes: sorting rewrites the chart's
`order_by` and re-runs its query, and a viewer holds neither half. Server-side
ordering was the alternative and it buys nothing yet — no other viewer control
asks for a re-query. Drill-down is off in the same mode (reserved for the drill
ticket). The table's filter row stays: the viewer holds the whole result, so
that one filters client-side and works.

**Container queries are still broken** (`@framework/ui/vite/island` drops the
app's Tailwind plugins, ticket 17's note). `NumberChart` collapses to one column
and overflows its card on a desk page while the same chart is fine in the SPA.
Not worked around here — the fix is upstream and hand-mirroring the classes
would be a second copy of them.

Measured, production build, JS + CSS raw (gzip):

| entry | ticket 17 | now |
| --- | --- | --- |
| `insights_chart` | 88.4 + 42.3 kB (31.3 / 6.8) | 89.5 + 45.8 kB (31.5 / 7.0) |
| `insights_dashboard` | 91.1 + 43.2 kB (32.3 / 7.0) | 110.1 + 46.7 kB (37.5 / 7.2) |

156.8 kB against the 160 kB budget: the filter stack (the control, the operator
and value pickers, `filter_utils`) is 19 kB of it. The next entry that grows
should re-pin the budget from a measured build rather than trim presentation.

### For ticket 22

"Duplicate to edit" is one entry in `menuOptions` in `DashboardIsland.vue`,
gated on `doc.can_duplicate` the way "Edit in Insights" is gated on
`doc.can_edit` — the overflow menu only renders when the list is non-empty, so a
pure viewer still sees nothing.
