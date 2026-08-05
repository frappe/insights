# 17 — Dashboard island and viewer endpoints

Type: task
Status: ready-for-agent
Blocked by: 14, 15, 19
Spec: [spec-insights-foundation.md](../spec-insights-foundation.md), "Viewer data endpoints" and "Island presentation and the desk-page split"

## What to build

A desk user with no Insights role views a dashboard mounted on a desk page.

A small set of viewer endpoints serves island consumption: fetch a dashboard
(items, layout, capability flags), fetch a chart (config), fetch chart data
(results). Plain `frappe.whitelist()`, no role check. Each endpoint resolves
the reference through the resolver, checks read permission on the content doc
through `frappe.has_permission`, and executes under the doc's
`data_authority`. Capability flags (can edit, can duplicate) drive the
island's rights-gated affordances, so the client never guesses. The
endpoints never expose the query definition. Existing role-gated endpoints
stay as they are for the authoring app.

The `insights.dashboard` island entry renders the chart grid in the saved
layout — per-card async, skeleton per card, cards fill in as queries return,
never a blank page — plus a quiet title row. One failing card degrades in
place, the rest of the page lives. Full presentation polish is ticket 18.

The size budget is re-pinned from this first clean dashboard-island build
plus slack, replacing the preset default.

## Acceptance criteria

- [ ] A user inside the audience, holding no Insights role, fetches dashboard
      and chart data through the viewer endpoints
- [ ] A user outside the audience gets the denied answer, identical to a
      missing reference
- [ ] A guest gets data only for `Public` content
- [ ] Endpoints accept logical id, slug, and docname through the resolver
- [ ] `ui_islands` declares `insights.dashboard`, and the island renders the
      grid on a desk page with per-card skeletons
- [ ] The dashboard response carries capability flags
- [ ] The size budget is re-pinned from the measured clean build
