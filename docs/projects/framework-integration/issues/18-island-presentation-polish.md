# 18 — Island presentation: the full viewer UX

Type: task
Status: ready-for-agent
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

- [ ] Filter values apply, show as chips, persist per user per dashboard,
      and survive reload
- [ ] The title row shows freshness and refresh works
- [ ] An empty-because-filtered card offers one-click filter reset
- [ ] A failing card shows retry in place while other cards render
- [ ] Denied and missing content render the identical page state
- [ ] "Edit in Insights" appears only with edit capability and opens a new
      tab; a pure viewer sees no authoring affordances
