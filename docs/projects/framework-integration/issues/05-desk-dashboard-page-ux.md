# Desk dashboard page UX

Type: prototype
Status: resolved
Blocked by: 04

## Question

The rewritten desk dashboard page — frappe-ui-first, mounted via the mechanism
ticket 02 picks. What does the user experience become?

- What the page shows: existing desk dashboard parity vs Insights-native
  dashboards; viewing, filtering, drill affordances.
- Edit story: where does "edit this dashboard" take the user (in place vs open
  in Insights)?
- Rollout: behind a v16 feature flag, coexisting with the legacy page.

Use /sketch-ux then /prototype; preserve the spirit of the core desk
experience — if Insights' dashboard UI needs to change to fit desk, change
Insights.

## Answer

Designed viewer-first: the primary persona is the desk consumer who never
opens Insights. The job is "see the state of my area and jump to what needs
attention" — the load-bearing emotional job is trust in the numbers, so the
page favors legibility, a freshness stamp, and drill that lands on desk
records, never in a query editor.

**Content: Insights dashboards only.** The rewritten page renders Insights
content exclusively. Legacy `Dashboard` widgets (number cards, quick lists,
shortcuts) are never re-rendered in the island — parity-first was rejected
as a parallel implementation of widgets we want to retire. The legacy page
stays as-is behind the flag; ticket 04's framework-owned renderer bridge
decides which page renders. Migrate/coexist for legacy content stays in the
fog.

**Entry and URLs.** Dashboards appear as workspace/module sidebar items;
placement is purely a site/workspace-editor concern — the bundle format
carries no placement hint. Routes: `/app/dashboard/<app>/<name>` for shipped
content (the bundle name is the slug), `/app/dashboard/<slug>` for
site-authored. The dashboard doctype grows a `slug` field — docname stays
hash, slug auto-generates from the title, unique, editable. Guardrail:
everything internal (sidebar links, mount props, chart→query references)
keeps using logical id/docname; editing a slug is cosmetic and breaks only
external bookmarks. This fills the hash→readable-URL hole ticket 04
reserved, Insights-internal as promised. No browsable all-dashboards
surface in v1.

**Page layout, by content priority.** 1) The chart grid, above the fold,
per-chart async — cards fill in as live queries return, skeleton per card,
never a blank page. 2) Sticky filter bar: applied values as visible chips,
per-user per-dashboard persistence. 3) Quiet title row: title, freshness
("as of 9:42"), refresh. 4) Rights-gated overflow: "Edit in Insights"
(new tab, only for users holding edit rights) and "Duplicate to edit" for
read-only shipped content — no in-desk builder, ever. A pure viewer sees
exactly two affordances: filter and click-a-chart.

**States.** Loading = skeleton cards in the saved layout. Empty-data =
per-card, with one-click filter reset when filters caused it. Denied = one
quiet page state naming the owner, identical whether the dashboard exists
or not (no existence leak). Error = the failing card degrades in place with
retry; one bad query never takes the page. Per-chart loading/empty/error
implementation will converge to frappe-ui charts v2 primitives when the
charts rewrite lands; dashboard-level states remain ours.

**Drill: split out.** Chart-segment click is reserved as the drill entry,
but the interaction — segment → break down by another dimension (ad-hoc
chart) → rows → open record — must be designed as one common layer serving
both Insights' own viewer and desk, so it moved to
[Drill-down interaction](11-drill-down-interaction.md), workable in
parallel. Known today: chart→record mapping doesn't work yet.

**Prototype dropped.** The viewer page and charts exist, the island mount
and shadow-root overlay behavior were proven in ticket 02's POC, and the
layout is convention — the only novel interaction now has its own ticket,
which may prototype the dialog with a mocked engine.

## Comments

2026-08-05 — the Insights-side spec
([spec-insights-foundation.md](../spec-insights-foundation.md)) revises the
route decision. The two route forms (`/app/dashboard/<app>/<name>` shipped,
`/app/dashboard/<slug>` site-authored) are replaced by a deferred choice:
every dashboard carries a slug (shipped slugs assigned at sync from the
logical name, app-qualified on collision), the resolver accepts logical id,
slug, and docname, and the URL pattern is picked when the framework-side
shell is built. Leading candidate: one flat `/app/dashboard/<slug>` route.
The rest of this answer stands.

2026-08-06 — the pattern, picked while building the framework-side shell:
`/app/dashboard-view/<reference>`, the route desk dashboards already live
at. `/app/dashboard/<slug>` was rejected because `dashboard` is the
`Dashboard` doctype's own route. Rendering inside the existing page means
every workspace link written so far keeps working and upgrades silently,
and desk gains no second dashboard route — the standalone
`insights-dashboard` page is gone. The page asks
`frappe.ui.get_dashboard_renderer(reference)` and branches on the answer: a
reference naming an existing `Dashboard` is legacy, everything else is
handed to Insights verbatim for the resolver to work out.
