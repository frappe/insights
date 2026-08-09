# Framework integration — decision map

This map records how Insights becomes the reporting layer of the Frappe
framework. It is a working document: the **Destination** states what "done"
means, **Decisions so far** indexes what is settled (one line per resolved
ticket, detail in the ticket), **Not yet specified** holds questions that are
in scope but not yet sharp enough to answer, and **Out of scope** records what
this effort deliberately excludes.

Tickets live in `issues/`, one question each. A ticket carries a `Type:`
(research, prototype, grilling, task), a `Status:`, and any `Blocked by:`
tickets. Findings from research tickets land in `research/`.

Charted 2026-08-01.

## Destination

The v3 framework-integration contract is fully decided: how Frappe apps (desk and
Vue-frontend) ship, reference, and render Insights charts and dashboards — the UX
of consuming Insights from those apps, and enough implementation shape to hand off
to spec. Insights is the reporting/charting layer of the framework; the core
framework experience is the fixed point — when something must change, Insights
changes.

## Notes

- Scope is v3 on `develop`. The `next`/v4 semantic rebuild stays out (see
  Out of scope).
- Assume Insights is present on every site. The presence guarantee (bundling,
  `required_apps`) is the framework team's decision, not this map's.
- Decisions must leave the codebase test-covered and deep-moduled.
- Target framework v16, behind feature flags (tentative — clarity expected later).
- One decision per working session.

## Decisions so far

Decided while charting, before tickets existed:

- **Insights owns the schema.** Apps depend on Insights' doctypes directly. No
  framework-owned fallback schema, no dual-engine authoring burden — the
  progressive-enhancement route was dropped when presence became assumed.
- **The engine stays in Insights.** Framework contributes rendering primitives
  (v2 charts, WIP in frappe-ui) and infrastructure (standard DuckDB sync, later).
  Layering: framework = infrastructure + UI primitives; Insights = the reporting
  layer.
- **v1 units = charts and dashboards.** Constraint: chart→query references stay
  stable and addressable so datasets can become first-class units later without a
  redesign.
- **Surfaces: desk first.** Rewrite the desk dashboard page, prove the base, then
  the Vue-frontend-app embed environment.
- **Permissions: author's choice per content.** Each dashboard/chart declares
  whether it runs under viewer's or author's permissions (desk reports run as
  author today; AR/AP-class content is role-gated, not row-filtered). Viewer mode
  is the engine's native permission application — it replaces hand-rolled
  providers like CRM's chart data provider.
- **Execution: live queries only for v1.** The DuckDB store switch is fog, pending
  framework's standard sync.

Resolved tickets:

- [Integration surface audit](issues/resolved/01-integration-surface-audit.md) — public-flag sharing + bare iframe shipped in Insights (no tokens, no embed SDK, no custom-block code yet); framework side: vue-islands parked in PR frappe#39773, `@framework/ui` shipped without charts, DuckDB snapshot sync merged (Report-only), desk dashboards still render frappe-charts via `chart_widget`.
- [Full-page mount mechanism for desk](issues/resolved/02-rendering-isolation-mechanism.md) — one mechanism at every granularity: dashboards and single charts both mount as Vue islands in a shadow root via framework's `mountVueIsland`. Iframe rejected (overlays can't escape the frame); vanilla/headless rejected (drill-down would mean a second UI on desk primitives). Requires Vue and frappe-ui to be framework-provided page singletons.
- [Runtime version policy](issues/resolved/07-runtime-version-policy.md) — framework's lockfile is the version authority for the whole runtime closure (Vue + frappe-ui + everything it drags in); versions reconcile at build time, so runtime skew is unreachable; within a framework major the runtime surface is append-only, so an Insights release just targets a major; the rule is "one framework runtime per page", loadable in desk and Vue-frontend apps alike. The runtime artifact itself doesn't exist yet — a framework deliverable for the build ticket.
- [Build ownership and island preset](issues/resolved/08-build-ownership-and-preset.md) — apps own their island builds; framework publishes an npm-installable Vite preset plus the runtime artifacts. Islands are native ESM linked through a desk-emitted import map (the convergence path for Vue-frontend apps); the generic enforcement is a per-entry size budget, import-boundary lint stays app-local; CSS splits like the JS — one shared runtime sheet via `adoptedStyleSheets`, islands ship only their own utilities; dev loop is preset watch + `hot_update` soft re-mount.
- [Mount and renderer API](issues/resolved/04-v1-contract-surface.md) — islands are hook-declared (`ui_islands`) and mounted through one generic `frappe.ui.mount_island(name, el, context)`; the envelope is structured by ownership (`host` framework-injected ambient, `props`/`on` island-specific, generic `update`/`unmount` handle, `configure(app)` fixes the app-config gap); references are logical ids (`{app}/{name}` for shipped content, resolved by Insights — hash docnames never cross the boundary); the renderer toggle is one framework-owned bridge that retires without an Insights release. "Island" is the ratified term, in `CONTEXT.md`.
- [Content lifecycle: author → ship → customize](issues/resolved/03-content-lifecycle.md) — one shipping channel: apps ship bundles of typed named documents (`insights/<bundle>/`, one JSON per query/chart/dashboard, logical-name references, workbook stays out of the format), synced as read-only standard docs via declarative reconcile; authoring = builder + "Export to app" + developer-mode round-trip, released through git; one append-only format major in `bundle.json`; template import-a-copy machinery retires. Customization split out to [Site customization of shipped content](issues/10-site-customization-of-shipped-content.md) with Duplicate as the interim floor.
- [Data access for desk-rendered content](issues/resolved/09-desk-data-access.md) — three-axis model (authoring / visibility / data authority), semantics only, store-agnostic. The gate is a visibility ladder (`Private | Specific Roles | Everyone | Public`) declared as fields on chart and dashboard, enforced through one `frappe.has_permission` seam — no `Insights User` role in the viewing path. `data_authority: Viewer | Author` defaults to `Viewer`, doc-declared, engine-enforced. Viewing implies no Insights access. Drill-down exposes the chart's query rows under the chart's authority, never the query definition.
- [Desk dashboard page UX](issues/resolved/05-desk-dashboard-page-ux.md) — viewer-first page rendering Insights dashboards only (legacy widgets never enter the island; legacy page stays behind the flag). Entry: workspace sidebar items + one route, `/app/dashboard-view/<reference>` — the existing desk dashboard route, so existing links upgrade in place (docname stays hash, slug editable, internal references stay on logical ids). Edit = "Edit in Insights" new-tab, rights-gated; "Duplicate to edit" for shipped. Per-card async states; denied leaks no existence. Drill split to [Drill-down interaction](issues/resolved/11-drill-down-interaction.md) as a common Insights+desk layer; prototype dropped as already-proven.
- [Shipping unit: bundle, or shipped workbook?](issues/resolved/24-shipping-unit-bundle-or-workbook.md)
  — the shipping unit is the workbook; "bundle" dies. Manifest becomes
  `workbook.json` (same keys); `Insights Workbook` carries `standard_id` +
  `is_standard` and syncs as the fourth reconciled doctype; the folder name is
  promoted to workbook identity; a standard workbook admits only standard items,
  so the container site global and its cleanup machinery die via patch. Renames
  `logical_id` → `standard_id` everywhere (amends ticket 04's vocabulary).
- [Workbook item lists: stored or derived?](issues/resolved/25-workbook-item-list-model.md)
  — derived, permanently; ratified rather than built (the server had already
  moved via `normalize_workbook.py` + the `as_dict` derivation). Ordering
  authority is `sort_order`/`folder` on items; lists ride the workbook fetch.
  The client-side residue (title mirror, index routes, reload-after-duplicate)
  is non-gating debt handed to the parked workbook-state-model effort.
- [The viewer seat: an Insights Viewer role?](issues/resolved/26-viewer-seat-role.md)
  — rejected. The seat means authoring (`check_app_permission` gates the
  builder SPA, never viewing); the ladder permanently owns audience on every
  surface; `Everyone` deliberately means any signed-in site user, with
  `Specific Roles` for narrower. The grant-source table is the controller's
  named model — a new source must earn a row, not a join. Two inputs recorded
  for the parked unified-permission-store effort: the table as its read-side
  starting spec, and team resource grants on content doctypes as a retirement
  candidate.
- [Who draws the desk page head?](issues/resolved/30-desk-page-head-ownership.md) — the
  island owns the whole desk page and desk draws no head on that route. Three
  findings decided it: desk's breadcrumbs are page-head markup (`page.html`), not
  navbar chrome; v16 already moved global chrome to the workspace dock (logo,
  search, notifications, user menu); and the `frappe.ui.Page` is what the sidebar
  and dock resolve visibility against, so the page stays and only its head goes.
  Framework gains `Page.toggle_page_head(show)`; `host` gains `breadcrumbs`
  (ancestors only), `navigate` and `set_title`. No island→shell channel was
  built — the island draws its own title. Amends ticket 05's page layout.
- [Who derives a chart's query?](issues/resolved/27-chart-query-derivation-owner.md) —
  the server, from `config`, at execution time; nothing persisted (option 4).
  Preview already round-trips, so derivation moves to the other end of an
  existing call: one endpoint family, chart name or inline config in, rows plus
  derived operations out; the client keeps zero derivation (SQL display and
  drill-down consume server-sent ops). The `data_query` artifact retires
  completely — field, cached query documents, permission rows, and
  `<chart>_data.json`, which leaves the format before it freezes. Route:
  parity-proven Python deriver → read paths switch → preview endpoint +
  client derivation deleted → retirement patch.
- [One dashboard renderer, one chart renderer](issues/resolved/31-one-dashboard-one-chart-renderer.md)
  — the viewer is the foundation; the builder becomes a viewer that can also
  write. `useViewerChart` generalizes into the one chart-read store (saved-name
  feed and inline-config feed); the `Chart`-aggregate adapter and `chart.ts`'s
  result half die; the renderer family below `ChartBody` survives as the one
  card set. One `DashboardView` in `dashboard/` owns grid, cards, filters, and
  capability-gated chrome; entry points (island, SPA route, public route) are
  ~20-line navigation shims. Viewer endpoints already serve guests through the
  ladder, so the public page needs no permission work — only the preview-image
  key moves into the controller. Order: shared/public first, SPA read page,
  builder last riding ticket 27 step 3.
- [What does Insights adopt from frappe-ui charts v2?](issues/resolved/32-charts-v2-adoption.md)
  — the seam cuts at the layer, not at the chart type. v2 chrome (`ChartCard`,
  `ChartContainer`, `ChartLegend`, `ChartTooltip`, states) dresses every Insights
  chart, Table and Map included; only the plot slot varies, between a v2
  component, an Insights plot on `useChart`, and no plot. Insights builds no
  ECharts option for a type v2 admits, and draws no chrome for a type it owns.
  The render swap goes first and ADR-0001's config split second, against that
  ADR's own order, because every unknown sits in the swap. v2 gains
  `xAxis.type: 'value'`; `show_scrollbar` is dropped; `split_by` stays wide
  because v2's `series` grouping takes a single `y`. frappe-ui's
  `spec/charts-scope.md` is the membership authority, and it rules Table and Map
  out of v2 on the model — which is what makes the plot slot permanent rather
  than a staging area. ADR-0001's "Blocked on" section was obsolete and is now
  amended. Specced as [spec-charts-v2.md](spec-charts-v2.md)
  (`ready-for-agent`), which branches `feat/charts-v2` off `develop` rather than
  riding the foundation branch.
- [Drill-down interaction](issues/resolved/11-drill-down-interaction.md) — one drill
  experience on every surface (viewer, desk island, builder preview);
  `DrillDown.vue` retires. Every segment click reduces to segment filters;
  entry is a two-item menu (View records / Break down by →, candidates = the
  pre-summarize result surface's dimensions minus pinned ones — the menu's
  click distribution reveals the common path). One dialog with an internal
  back-stack and breadcrumb, ephemeral. Breakdown = the existing Row chart,
  ad-hoc, click-recurses; records = all result columns in the viewer data
  table, with a per-row open-record control driven by server-derived
  `record_link` metadata (base site-DB table + surviving `name` column; the
  client never guesses). Guests get no drill in v1. Wire: stateless
  `viewer.get_drill_data(chart, dashboard?, filters?, drill_stack)` — plain
  values, never operations; server re-derives from `config` (ticket 27),
  slices, validates, applies; candidates piggyback on `get_chart_data`.
  Authoring extra: "open as query" into an ephemeral ad-hoc query, Insights
  surfaces only, edit-rights-gated. First shipped slice of
  [ticket 33](issues/33-query-building-server-side.md).
- **Ownership split** (settled during ticket 02) — framework owns the desk page shell, the mount contract, the shared runtime (Vue + frappe-ui + chart primitives), and the renderer toggle; Insights provides doctypes, engine, and a mountable UI artifact built against framework-provided externals. The seam is one call: framework's page asks Insights to mount into an element with host context. The Insights→desk bridge (is Insights installed? is the flag on? is this an Insights dashboard?) lives in framework, so Insights never knows about the fallback.

The framework-side foundation is specced from these tickets:
[spec-framework-foundation.md](spec-framework-foundation.md) (`ready-for-agent`).
The Insights-side foundation is specced from tickets 03, 04, 05, and 09:
[spec-insights-foundation.md](spec-insights-foundation.md) (`ready-for-agent`).

The drill-down layer is specced from ticket 11:
[spec-drill-down.md](spec-drill-down.md) (`ready-for-agent`).

## Implementation — the foundation branch, 2026-08-05

Tickets 12–23 built the Insights-side and SPA-side foundation the specs above
called for. Implementation tasks, not decisions — one line per ticket for what
shipped, not how:

- [Repoint the SPA at framework's frappe-ui](issues/resolved/12-spa-repoint-framework-frappe-ui.md) — `frontend/package.json` links frappe-ui from the framework checkout (branch `desk-islands`); production and dev builds work with one frappe-ui in the graph.
- [Navigation seam: decouple the viewer graph from the SPA router](issues/resolved/13-navigation-seam-router-decoupling.md) — the chart and dashboard stores resolve navigation through an injected `helpers/navigation` seam; an app-local ESLint boundary keeps the router and the workbook store out of the viewer graph.
- [Tracer bullet: a minimal `insights.chart` island](issues/resolved/14-chart-island-tracer.md) — the first island builds, registers under `ui_islands`, and mounts a chart in a shadow root on a desk page, live theme switch and idempotent unmount included.
- [Visibility ladder](issues/resolved/15-visibility-ladder.md) — `visibility`/`visible_to_roles` on chart and dashboard, enforced as one grant source inside `InsightsPermissions`; `is_public` migrates onto the `Public` rung.
- [Data authority](issues/resolved/16-data-authority.md) — `data_authority: Viewer | Author` on `Insights Chart v3`, read off the stored document and enforced in `InsightsTablev3.get_ibis_table`; no wire parameter can override it.
- [Dashboard island and viewer endpoints](issues/resolved/17-dashboard-island-viewer-endpoints.md) — role-free viewer endpoints serve dashboard, chart, and chart data by resolver reference; the `insights.dashboard` island renders the saved grid with per-card skeletons.
- [Island presentation: the full viewer UX](issues/resolved/18-island-presentation-polish.md) — sticky filter bar, freshness/refresh, per-card empty/error states, the quiet denied state, and the rights-gated "Edit in Insights" menu.
- [Logical-id resolver and slug](issues/resolved/19-logical-id-resolver-slug.md) — `insights/resolver.py` resolves logical id, slug, or docname to a document, with a denied read indistinguishable from an unknown reference.
- [Bundle shipping and declarative reconcile](issues/resolved/20-bundle-shipping-reconcile.md) — `insights/bundles.py` reconciles an app's `insights/<bundle>/` folders into standard documents on migrate and app-install, idempotently.
- [Export to app and the developer-mode round-trip](issues/resolved/21-export-to-app-roundtrip.md) — "Export to app…" in the workbook menu writes a dashboard's closure into a bundle; a developer-mode save on a standard doc writes back to the same file.
- [Duplicate to edit](issues/resolved/22-duplicate-to-edit.md) — the v1 customization floor: duplicating a shipped dashboard copies its closure into a private, user-owned workbook.
- [Template migration and glossary](issues/resolved/23-template-migration-glossary.md) — the four ERPNext templates re-ship as bundles; the version/checksum update channel and the import ceremony retire; `CONTEXT.md` gains Bundle, Standard content, and Slug.

## Second wave — 2026-08-06

Raised by the 2026-08-06 review of the foundation branch: the implementation
proved the contract but surfaced three model questions (tickets 24, 25, 26),
gating the refactor of the branch, not its feasibility. All three are resolved
and indexed under Decisions so far. The reshape is specced from them:
[spec-branch-reshape.md](spec-branch-reshape.md) (`ready-for-agent`,
re-specced 2026-08-07 — see below).
Tickets 27 and 31 resolved together on 2026-08-06 and specced as
[spec-one-renderer.md](spec-one-renderer.md), which **shipped 2026-08-07**,
all five steps: the Python deriver, the read-path switch, `DashboardView`
with the preview key moved into the controller, the builder on the read
store, and the cache retirement patch.

Both specs said the reshape lands first. One-renderer landed first anyway,
which cost nothing — it removed code the reshape would have renamed. Three
further commits then took work off the reshape, each for its own reason:
`29a1e82f` moved the container workbook's identity onto the document to fix a
sync race (this spec's identity pin and its migration patch, built early),
`3c0d5edb` retired `is_public` and `api/shared.py` so every read now goes
through the permission controller, and `454d8716` removed a duplicated helper.

The reshape was re-specced 2026-08-07 against the branch as it now stands. What
changed: the workbook already carries its identity, so only `is_standard` and
the field rename remain; the grant-source table is exhaustive and splits
bypasses from sources, with a preview-key row; the resolver has four reference
forms, not three; the rename scope grows to one-renderer's suites and to seven
user-facing strings in the Export dialog that the spec had said would not
change; and the grep gate learns that a JavaScript asset bundle is not a
shipping unit.

**The reshape shipped the same day**, in six commits — see
[spec-branch-reshape.md](spec-branch-reshape.md) for the map of commit to
section. The format is unfrozen no longer: `workbook.json` and `{app}/{folder}`
identity are its first public shape, so an app may now ship content against the
branch.

Three findings came out of the work rather than the spec, and are worth keeping:

- **Writing the grant-source table down found two grant sources missing from
  it** — `query -> alert` inheritance, and team membership on `Insights Team`,
  neither of which ticket 26 knew about. That is the drift the docstring exists
  to stop, caught on its first day.
- **A permission leak, fixed** (`536ae175`): an empty team list matched every
  team's resource grants instead of none, so a user in no team read every
  dashboard, chart, data source and table granted to any team — with team
  permissions *enabled*. `TEAM_BASED_PERMISSION_DOCTYPES` went with it: unread,
  and its claim was untrue.
- **Reconciling the workbook put it in the content's flat per-app namespace**,
  so a folder and a chart of the same name is now a clash that fails loudly.
  That is the Standard ID rule made enforceable, not a new restriction.

Still open in this wave:

- [Which lockfile is the runtime version authority?](issues/28-runtime-version-authority.md)
  — raised when every frappe-ui island died at import. Ticket 07 says framework's
  lockfile governs the whole closure, but `link:./frappe-ui` lets the walk cross
  into a tree a second lockfile governs. The build now fails loudly on a bad
  crossing; the second authority stands, and 07's "runtime skew is unreachable"
  is false as written.
- [What ambient does the host owe an island?](issues/29-host-ambient-for-islands.md)
  — ticket 04 gave the envelope a `host` slot without saying what goes in it.
  Three instances now: frappe-ui icons need a sprite no shadow root can reach,
  number formatting drops Indian grouping the SPA applies, and ticket 30 added
  the breadcrumb trail and desk routing. The third was designed rather than
  patched and widened the slot from values to capabilities; the rule that stops
  the fourth still does not exist.

## Not yet specified

- **Datasets as first-class shippable units** — apps ship curated queries/models
  users explore and build their own charts on. Graduates once the contract shape
  settles.
- **Code-first authoring API** — minimal code APIs doing the builder's job for dev
  authors. Purely additive; the one coupling is export-format stability (the
  content-lifecycle ticket carries that constraint).
- **Contextual/inline charts UX** — charts in doctype views, list headers,
  sidebars. The *mechanism* is settled (same island), but filters, doc-context,
  and drill-down semantics in a form are not. Sharp only after the full-page base
  exists.
- **Switching Insights' data store to framework's standard DuckDB sync** — and the
  longer direction of DuckDB as default execution engine. Hangs on framework work
  that doesn't exist yet.
- **Legacy desk `Dashboard` / `Dashboard Chart` content** — migrate, coexist, or
  deprecate, once Insights' doctypes are the standard.
- **v16 flag/rollout strategy** — expected to sharpen as the desk work lands.

## Out of scope

- **`next`/v4 semantic rebuild** — shelved by the 2026-07-29 pivot toward v3 for
  ERPNext users.
- **Query-building location, workbook state model, test strategy, feature
  prioritization** — separate efforts. Where one constrains integration, the
  position is stated in the ticket as an input rather than re-decided here.
- **Financial statements** — auditing, not analysis; not replaced by Insights.
- **Insights presence guarantee** (bundling, `required_apps`) — the framework
  team's decision; this map assumes presence.
- **Unified permission-rule store** (`subject × object × action`, an Insights
  permission-model overhaul with a possible framework RFC) — its own future
  effort. The [desk data access](issues/resolved/09-desk-data-access.md) decision is
  store-agnostic behind the `has_permission` seam, so the store can land
  without touching the integration contract. Recorded requirements and inputs:
  role-based edit grants; the grant-source table from
  [ticket 26](issues/resolved/26-viewer-seat-role.md) as the read-side starting spec;
  team resource grants on content doctypes as a retirement candidate (teams
  govern data objects only).
