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

- [Integration surface audit](issues/01-integration-surface-audit.md) — public-flag sharing + bare iframe shipped in Insights (no tokens, no embed SDK, no custom-block code yet); framework side: vue-islands parked in PR frappe#39773, `@framework/ui` shipped without charts, DuckDB snapshot sync merged (Report-only), desk dashboards still render frappe-charts via `chart_widget`.
- [Full-page mount mechanism for desk](issues/02-rendering-isolation-mechanism.md) — one mechanism at every granularity: dashboards and single charts both mount as Vue islands in a shadow root via framework's `mountVueIsland`. Iframe rejected (overlays can't escape the frame); vanilla/headless rejected (drill-down would mean a second UI on desk primitives). Requires Vue and frappe-ui to be framework-provided page singletons.
- **Ownership split** (settled during ticket 02) — framework owns the desk page shell, the mount contract, the shared runtime (Vue + frappe-ui + chart primitives), and the renderer toggle; Insights provides doctypes, engine, and a mountable UI artifact built against framework-provided externals. The seam is one call: framework's page asks Insights to mount into an element with host context. The Insights→desk bridge (is Insights installed? is the flag on? is this an Insights dashboard?) lives in framework, so Insights never knows about the fallback.

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
- **frappe-ui charts migration** — already in flight, needs no decision.
- **Insights presence guarantee** (bundling, `required_apps`) — the framework
  team's decision; this map assumes presence.
