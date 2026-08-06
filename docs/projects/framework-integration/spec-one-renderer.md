# Spec: one renderer — the server derives, the viewer is the foundation

Status: ready-for-agent
Target: the Insights foundation branch, after
[spec-branch-reshape.md](spec-branch-reshape.md) lands (that reshape renames
modules this spec touches).

Sources: the resolved tickets
[27](issues/27-chart-query-derivation-owner.md) (query derivation owner) and
[31](issues/31-one-dashboard-one-chart-renderer.md) (one dashboard renderer).
Glossary: `CONTEXT.md` — Standard content, viewer, island, visibility ladder,
data authority.

## Problem Statement

A chart's rows come from a query no one on the server can produce. The client
derives it, persists it as a cached query document, and every server consumer
— chart data, the viewer endpoints, the shipped format — stands on that cache.
Every chart in all four shipped workbooks broke this way: exported with an
empty cache, they drew their raw source tables and called it the chart.

On top of that cache, the frontend grew two of everything. A dashboard renders
through the builder stack on three surfaces and through the island viewer on
the fourth. A chart card has two data layers for the same content, and the
viewer's layer must impersonate the builder's — a reactive object stubbing a
dozen methods with no-ops — to be allowed to render.

## Solution

The server derives a chart's query from its config at execution time. Nothing
is persisted, so the cache and its whole failure class retire: the field, the
cached query documents, the permission rows, and the per-chart data file in
the shipped format.

The viewer becomes the one foundation. One chart-read store with two feeds —
a saved chart name, or unsaved config for the builder's preview — and one
`DashboardView` surface that owns everything inside the page, with chrome
gated by server-granted capabilities. The desk island, the public page, the
SPA read page, and the builder are entry-point shims over the same surface.
The builder is a viewer that can also write.

## User Stories

1. As an app developer, I want a chart I author as JSON to render correctly without a builder session, so that shipping content never depends on a browser having visited it.
2. As an app developer, I want a chart's shipped folder to carry one file per chart, so that the format has no cache file I must remember to materialize.
3. As a site user, I want a chart's rows to always match its config, so that a stale cache can never show me wrong numbers.
4. As a desk user with no Insights role, I want dashboard cards to load through the same path as everyone else's, so that what I may see is decided by the ladder, not by which surface I opened.
5. As a viewer of a public dashboard, I want the public page to be the same surface as the desk page, so that filters, states, and freshness behave identically everywhere.
6. As a viewer on any surface, I want refresh, export-as-image, and duplicate offered when I hold the capability, so that what I can do depends on my rights, not on which page I found.
7. As a viewer without edit rights, I want no editing affordance rendered at all, so that the surface never dangles an action I cannot take.
8. As an editor, I want "Edit in Insights" on any surface where I hold edit rights, so that reaching the builder never requires knowing the workbook URL.
9. As a chart author in the builder, I want the preview to update on every config change without saving, so that authoring stays as responsive as it is today.
10. As a chart author, I want the SQL display to show the query the server actually ran, so that what I debug is what executed.
11. As a chart author, I want drill-down to fork the server-derived operations, so that the drill result agrees with the card it came from.
12. As a chart author, I want sort and date-granularity changes to be config edits, so that every re-shaping of data goes through the one deriver.
13. As a script or API author, I want to create a working chart by writing config alone, so that automation can produce content the UI treats as first-class.
14. As an Insights developer, I want exactly one derivation of the chart query in the codebase, so that config and rows cannot drift.
15. As an Insights developer, I want one chart-read store consumed by every surface, so that a rendering fix lands everywhere at once.
16. As an Insights developer, I want the card components to take the read store natively, so that no surface must impersonate a builder aggregate to render.
17. As an Insights developer, I want entry points restricted to navigation context, so that page content can never fork per surface again.
18. As a site administrator, I want the cached query documents removed by migration, so that retired machinery leaves no orphans behind.
19. As a dashboard consumer on a slow connection, I want per-card loading and error states on every surface, so that one slow query never blanks the page.
20. As a preview-image service, I want the preview key honored on the viewer path, so that thumbnails keep rendering after the old public read path retires.

## Implementation Decisions

### The deriver: server-side, from config, at execution time

- One Python deriver turns a chart's config into its operations JSON: the
  source query's operations, plus dashboard filters, plus the chart's own
  summarize/pivot, plus order-by. It covers all seven chart types (axis with
  split-by, number, donut, funnel in both modes, table with pivot, map,
  bubble) — a port of the client derivation, which is deleted.
- The deriver runs at execution time. Its output is never persisted. Chart
  data (`get_data`) and the viewer's chart-data endpoint call it instead of
  reading the cached query.
- The interim "unconfigured chart throws" guard changes meaning: unconfigured
  now means the config cannot derive, never an unfilled cache.

### The preview contract: one endpoint family, derived operations out

- One endpoint family serves chart data everywhere. Saved surfaces pass a
  chart reference; the builder's preview passes unsaved config plus the
  source query reference. Same deriver, same response shape behind both.
- The response carries rows, columns, and the derived operations. The client
  keeps zero derivation: the SQL display renders what the server sent, and
  drill-down forks the server-sent operations into a drill query.
- Derived operations cross the wire only on the authoring endpoint, which is
  gated on authoring rights. The viewer contract is unchanged: no viewer
  response carries operations or SQL. Drill-down on read surfaces stays
  ticket 11's business.
- Preview responsiveness is preserved by construction: the preview already
  round-trips to execute, so moving derivation server-side adds no call.

### The cache retires completely

- The chart's data-query link field is dropped, along with the code that
  fills and reads it. A patch deletes every cached query document a chart
  references — they are chart-owned caches, referenced nowhere else.
- The permission controller loses its data-query grant rows. Per the named
  model, the row leaves the grant-source table with the source.
- The shipped format carries one file per chart. The per-chart data file is
  neither written by export nor read by sync — no compatibility read, because
  this lands before the format freezes (same rule as the manifest rename).
- Duplicate drops its data-query handling.

### The chart-read store: one store, two feeds

- The island viewer's chart composable generalizes into the one chart-read
  store. Behind one interface: a saved-reference feed (viewer endpoints,
  used by desk, public, and SPA read surfaces) and a config feed (the
  authoring endpoint, used only by the builder). Above the fetch the store
  is identical: result, loading/error/empty state, freshness, priority-queued
  execution.
- The builder-aggregate adapter dies. Card components take the read store
  natively; the builder passes the same shape plus its editing context.
- The builder's chart store shrinks to authoring state: the document, config
  editing, save. Its derivation-and-result half is deleted.

### One `DashboardView`, entry points as shims

- One `DashboardView` component owns everything inside the page: the grid,
  the cards, the filter bar, and the chrome actions — refresh, export as
  image, edit, open workbook, duplicate. It lives with the dashboard
  components as their core; the islands folder keeps only desk mount glue.
- Chrome is gated by what the dashboard endpoint grants (`can_edit`,
  `can_duplicate`, the workbook pointer, the ladder rung) — a property of
  the surface, never of the host. An ungranted capability does not render.
- Entry points are mount shims of roughly twenty lines, allowed to carry only
  navigation context: the island shim carries desk mount lifecycle and host
  ambient; the SPA route shim carries breadcrumbs and the document title; the
  public route shim carries reference resolution from the URL.
- The standing rule: anything that renders inside the page box goes in
  `DashboardView` behind a capability. Only navigation context may live in a
  shim.

### Access: the viewer path already serves everyone

- The viewer endpoints are guest-callable and decide access through the
  visibility ladder, so the public page moves onto them with no permission
  work. A guest reaches the Public rung through the same code as everyone
  else.
- The preview-image key moves from the old public read path into the
  permission controller, so thumbnail rendering rides the viewer path. The
  old public dashboard read path retires once nothing calls it.

### Order of work

Each step ships on its own and leaves the app whole:

1. **Deriver + parity.** The Python deriver lands with a parity test that
   diffs its output against every populated cache — shipped workbooks and
   fixtures. No behavior changes.
2. **Read paths switch.** Chart data and the viewer endpoint derive instead
   of reading the cache. The client still writes the cache; nothing reads it.
3. **Public and SPA read surfaces move.** `DashboardView` is extracted from
   the island surface; the public page and the SPA read page become shims
   over it. The preview key moves. (This step is independent of steps 1–2.)
4. **Builder moves.** The authoring endpoint lands; the builder consumes the
   read store's config feed; the client derivation, the builder-aggregate
   adapter, and the builder-coupled card path are deleted.
5. **Retirement.** The field, the cached documents (patch), the permission
   rows, and the format's per-chart data file.

## Testing Decisions

Tests assert external behavior at the endpoint seam, never the deriver's
internals — a good test asks "does this chart's data match its config" and
"does this response carry what this caller may see", not "which operations
were produced".

- **Endpoint layer (existing seam).** The viewer API suite extends: chart
  data derives from config; the unconfigured-chart test now means bad config,
  not empty cache; every existing ladder, authority, filter-routing, and
  no-query-leaves assertion must pass unchanged. The authoring endpoint gets
  cases at the same layer: config in, rows plus derived operations out,
  denied without authoring rights, and no derived operations on any viewer
  response.
- **Parity (the one new seam, temporary).** Deriver output diffed against
  the persisted caches for every populated chart — the shipped workbooks and
  factory fixtures are the oracle for the port, across all seven chart
  types. The seam dies with the caches at step 5.
- **Sync and export (existing seams).** Export writes no per-chart data
  file; sync reads none; the format fixture ships without them. The existing
  suites adjust rather than grow.
- **Frontend structure.** No unit-test infrastructure is added. The
  one-surface rule is enforced structurally, the way the navigation seam
  already is: a lint boundary keeps card components importable only from the
  dashboard surface, so a shim that grows content fails the build.

## Out of Scope

- Drill-down on read surfaces — ticket 11's common layer.
- frappe-ui charts v2 as the per-card rendering primitive.
- The legacy desk widget dashboard.
- The host-ambient contract (ticket 29) — the island shim consumes it,
  whatever it says.
- Any change to the viewer response contract beyond capability flags already
  present.

## Further Notes

- Ticket 27's fear that the builder "edits the data query as a query" turned
  out false: sort and granularity edits write to config and re-derive. There
  is no pipeline-editing surface to preserve.
- The parity harness is the only moment the old and new derivations coexist
  as oracle and candidate — it is also the first test coverage the seven
  chart types have ever had. Do not skip it to save time; it is what makes
  step 2 safe.
- Steps 1–2 and step 3 are independent lines; step 4 needs both. If the
  reshape spec and this one are in flight together, land the reshape first —
  it renames the sync/export modules this spec edits.
