# Spec: Insights-side island foundation

Status: ready-for-agent
Target: `apps/insights`, branch off `develop`, Insights v3.

This spec covers the Insights-side deliverables of the framework-integration
effort. The framework-side foundation is
[spec-framework-foundation.md](spec-framework-foundation.md) — this spec
builds on its contract and never restates it.

Sources: [map.md](map.md) and the resolved tickets
[03](issues/resolved/03-content-lifecycle.md) (content lifecycle),
[04](issues/resolved/04-v1-contract-surface.md) (mount and renderer API),
[05](issues/resolved/05-desk-dashboard-page-ux.md) (desk dashboard page UX),
[09](issues/resolved/09-desk-data-access.md) (desk data access).
Ticket [10](issues/10-site-customization-of-shipped-content.md) is open —
Duplicate is the ratified interim customization floor. Ticket
[11](issues/resolved/11-drill-down-interaction.md) is open — drill-down is an open
seam, reserved but not designed here.
Glossary: `CONTEXT.md` (Island, Visibility, Data Authority are ratified terms).

## Problem Statement

Framework now ships the island foundation, but Insights has nothing to mount.
The chart and dashboard modules import the SPA router, so a chart-only island
once measured 2.3 MB of JS. Content references cross app boundaries as hash
docnames, which no consumer app can ship in code. Shipped content arrives
through the template gallery as per-site copies with a version/checksum update
model. Every data endpoint requires the `Insights User` role, so an ordinary
desk user cannot fetch chart data at all. The standalone SPA pins its own
frappe-ui version, so the SPA and a future island could disagree with
framework's runtime. Until these five gaps close, no desk page can render an
Insights dashboard.

## Solution

Insights ships two islands, `insights.dashboard` and `insights.chart`,
declared through the `ui_islands` hook and built with framework's Vite preset.
The island entries link a router-free viewer graph, and an app-local
import-boundary lint keeps it that way. One server-side resolver turns every
reference form — logical id `{app}/{name}`, slug, docname — into the
site-local document, so hash docnames never cross the contract boundary. Apps
ship content as bundles of typed named documents, synced on migrate as
read-only standard docs through declarative reconcile. A visibility ladder and
a data-authority field on the content, enforced through `frappe.has_permission`
and the engine, let any declared audience view content with no Insights role.
The dashboard island renders the whole page body — title row, filter bar,
chart grid, states — so the desk page shell is one mount call. The SPA build
follows framework's frappe-ui version, so both build targets share one
version. Site customization of shipped content is Duplicate, nothing more.

## User Stories

1. As an app developer, I want to ship dashboards, charts, and queries as JSON files in my app, so that my analytics release through git like the rest of my app.
2. As an app developer, I want internal references stored as logical names, so that my content survives export, sync, and site moves without dangling references.
3. As an app developer, I want shipped content synced on migrate, so that a reference from my app can never point at content that does not exist.
4. As an app developer, I want items removed from my bundle deleted on migrate, so that sites never accumulate orphaned standard content.
5. As an app developer, I want my standard docs deleted on app uninstall while user copies survive, so that uninstall is clean but never destroys user work.
6. As an app developer, I want to author in the Insights builder and export to my app, so that I never hand-write dashboard JSON.
7. As an app developer, I want standard docs editable in the builder on a developer-mode bench with saves written back to my app folder, so that iteration is a normal edit-save loop.
8. As an app developer, I want an append-only bundle format with one integer version, so that my shipped content stays importable across Insights releases.
9. As a desk user, I want to view a dashboard my roles admit without any Insights role, so that viewing needs nothing beyond the declared audience.
10. As a desk user, I want each card to load independently with a skeleton, so that one slow query never blanks the page.
11. As a desk user, I want a failing card to degrade in place with a retry, so that one bad query never takes the page down.
12. As a desk user, I want filter chips with per-user persistence, so that my dashboard opens the way I left it.
13. As a desk user, I want a freshness stamp and a refresh action, so that I can trust the numbers I act on.
14. As a desk user, I want empty-data cards to offer a one-click filter reset when filters caused the empty result, so that I recover without hunting.
15. As a desk user, I want denied and missing dashboards to look identical, so that access control leaks no existence information.
16. As a desk user with edit rights, I want "Edit in Insights" to open the builder in a new tab, so that desk never hosts a builder.
17. As a desk user, I want "Duplicate to edit" on shipped content, so that I can customize a copy while the standard stays pristine.
18. As a site administrator, I want visibility declared on the content itself, so that embedding a chart never forces a broad role grant.
19. As a site administrator, I want guest access decided inside the permission controller by the `Public` rung, so that no endpoint carries its own guest logic.
20. As an Insights author, I want a visibility ladder — `Private | Specific Roles | Everyone | Public` — on charts and dashboards, so that I declare an audience once and every surface honors it.
21. As an Insights author, I want charts on my dashboard to inherit the dashboard's audience, so that I declare visibility once per dashboard.
22. As an Insights author, I want `data_authority` on my content with `Viewer` as default, so that embedded content is safe unless I deliberately escalate.
23. As an Insights author, I want a loud confirmation when I combine a wide audience with Author authority, so that I never expose rows by accident.
24. As an Insights author, I want drill-down bounded by my query's result columns, so that the rows I publish are exactly the rows I selected.
25. As an Insights developer, I want the island entries free of the SPA router, so that the islands stay within the size budget.
26. As an Insights developer, I want an import-boundary lint on the island entry graph, so that a future import cannot silently recouple it.
27. As an Insights developer, I want the SPA to build against framework's frappe-ui version, so that two frappe-ui versions never exist across my build targets.
28. As an Insights developer, I want islands registered unconditionally with zero fallback awareness, so that the renderer bridge retires without an Insights release.
29. As a framework desk page, I want to mount a dashboard by logical id or slug with one call, so that the page shell holds no Insights knowledge.
30. As a framework desk page, I want navigation intents surfaced through the `on` callbacks, so that the host decides how to open Insights.

## Implementation Decisions

### Island entries and router decoupling

- Two island entries, `insights.dashboard` and `insights.chart`, built with
  framework's preset (`@framework/ui/vite/island`) as a second Vite build
  target beside the SPA build. Declared in `hooks.py`:
  `ui_islands = {"insights.dashboard": "<base>.island.js", "insights.chart": "<base>.island.js"}`.
- Each entry exports the mount contract:
  `mount(el, { host, props, on }) → { update(props), unmount() }`. The entry
  uses `configure(app)` to register the plugins the viewer graph needs.
- Registration is unconditional. No flag check, no fallback awareness — the
  renderer bridge owns all conditions.
- The viewer graph must not import the SPA router. The chart and dashboard
  stores currently import the router for navigation. Navigation becomes an
  injected seam: one small navigation module with two providers — the SPA
  provides its router, the island entry provides an adapter that raises
  `on` callbacks (`onNavigate`) or opens a new tab. Components resolve
  navigation through injection, never through a router import.
- Import-boundary lint, app-local: the island entry graphs must not import
  the router module or SPA page modules. Enforced with an ESLint
  `no-restricted-imports` rule (or an equivalent check) that runs in the
  build. The preset's size budget is the backstop, the lint is the fast
  signal.
- Bare imports in island code are limited to the specifiers framework
  registers as runtime (`vue`, `vue-router`, `frappe-ui`, `echarts`, …).
  Everything else bundles into the island and counts against the budget.
- The size budget is re-pinned from the first clean dashboard-island build
  plus slack, replacing the preset's default.
- Dark mode: the island root element inside the shadow root carries
  `data-theme` from `host.theme` and updates live. Tailwind's dark selector
  is a descendant selector, so the attribute must sit inside the shadow
  root, not on the host element.

### Island presentation and the desk-page split

- The split: framework's desk page provides desk chrome, the route, the
  renderer bridge branch, and one container element. The island renders the
  entire page body. The shell holds no Insights knowledge beyond the mount
  call.
- The `insights.dashboard` island renders, in content priority order: the
  chart grid (above the fold, per-card async, skeleton per card), a sticky
  filter bar with applied values as chips and per-user per-dashboard
  persistence, a quiet title row (title, freshness stamp, refresh), and a
  rights-gated overflow menu.
- The overflow menu: "Edit in Insights" opens the builder in a new tab and
  renders only for users who hold edit rights and pass the app permission
  check. "Duplicate to edit" appears on read-only shipped content. There is
  no in-desk builder.
- Props for `insights.dashboard`: the content reference, optional initial
  filter state, read-only versus interactive. Props for `insights.chart`:
  the content reference and optional filter state. Both opaque to framework.
- Callbacks: `onError` as notification (the island renders its own error
  states), `onNavigate` for open-in-Insights-class intents, filter-change
  notifications.
- States: loading is skeleton cards in the saved layout. Empty-data is
  per-card, with one-click filter reset when filters caused it. Denied is
  one quiet page state, identical whether the content exists or not. Error
  degrades the failing card in place with retry.
- Per-card loading/empty/error rendering converges to frappe-ui charts v2
  primitives when the charts rewrite lands. Dashboard-level states stay
  Insights-owned.
- Chart-segment click is reserved as the drill entry. The interaction is
  ticket 11's open seam and stays internal to the island, so it lands later
  without a contract change.
- The dashboard doctype grows a `slug` field on every dashboard: unique,
  auto-generated from the title for site-authored content, assigned at
  sync for shipped content (the logical name, app-qualified only on
  collision, with a sync warning). The docname stays a hash. Internal
  references (sidebar links stored by consumers, mount props, chart→query
  references) never use the slug — editing a slug breaks only external
  bookmarks. Standard docs are read-only, so shipped slugs are stable.
- The desk URL pattern is deferred to shell-build time (the shell is
  framework-side, out of this spec). The leading candidate is one flat
  route, `/app/dashboard/<slug>`, matching desk's flat workspace URLs.
  The slug field and the three-form resolver keep that choice cheap until
  the first release in which an app ships a dashboard link.

### Logical ids and the resolver

- One server-side resolver turns a reference into the site-local document.
  Accepted forms, for any dashboard: logical id `{app}/{name}`, slug, and
  docname. Accepting all three keeps the desk route pattern a free choice
  at shell-build time. Hash docnames never cross the contract boundary —
  consumer apps ship logical ids only.
- Shipped docs carry their logical id in a dedicated field, the lookup key
  the resolver uses. This extends the `from_template` convention already in
  the codebase.
- Resolution policy under the v1 customization floor: a logical id resolves
  to the standard doc, always. A Duplicate is an ordinary user document with
  its own identity and is never returned for the shipped id. Ticket 10 owns
  any future shadowing policy — it changes the resolver only.
- A failed resolution and a denied read return the same answer, so the
  resolver leaks no existence information.
- One level down, a chart references its query by name inside Insights'
  documents. The mount API never flattens a chart into inline query config.
  This keeps queries addressable for the datasets-later promotion.

### Bundle format and shipping

- An app ships `insights/<bundle>/` folders. Each bundle holds typed
  subfolders (`query/`, `chart/`, `dashboard/`) with one JSON file per item,
  named by logical name, plus a `bundle.json` (title, `required_apps`, one
  integer format version).
- Item names are unique per app. `{app}/{name}` is a flat namespace. Bundle
  folders are organization, not identity.
- Internal references — dashboard→chart, chart→query — are logical names,
  never docnames. The workbook does not appear in the format.
- Volatile fields are stripped on export: no `modified`, no `owner`, no hash
  names, no cached results. Diffs are content-only.
- Exports assign each dashboard item a stable vendor-owned key. Cheap,
  append-only, and the hook a future keyed customization model hangs on.
- Format discipline: the version is owned by Insights, append-only within a
  major. Importers tolerate unknown keys. A breaking change bumps the major
  with a file-level migration. No per-file or per-doctype versions.

### Sync: declarative reconcile

- Bundles sync on `after_migrate` and `after_app_install` into real Insights
  documents flagged standard, carrying their `{app}/{name}` identity.
  Discovery walks the installed apps' `insights/` directories — real
  installed apps, not a fakeable seam.
- Reconcile is declarative: new items are created, changed items are
  updated, items removed from the bundle are deleted on migrate.
  `before_app_uninstall` deletes the app's standard docs. User copies
  survive both.
- Sync is idempotent. Running it twice changes nothing.
- Standard docs are read-only on a site outside developer mode.
- Rename is not a v1 feature. The logical name is the identity. A
  `renamed_from` alias can enter the format later if demand shows.
- Standard docs attach to one site-managed, Administrator-owned workbook per
  bundle, created by sync and titled from `bundle.json`. The workbook stays
  out of the shipping format — this container is a site-side artifact that
  lets the workbook-centric builder open standard content. The bundle folder
  sets container granularity only; identity stays `{app}/{name}`. (Pinned by
  this spec, see Further Notes.)

### Authoring flows

- Birth: author as normal content in the builder, then "Export to app…"
  writes the closure (dashboard + charts + queries) into the chosen app's
  bundle and flags the docs standard. The action requires a developer-mode
  bench with the target app installed.
- Iteration: on a developer-mode bench, standard docs are editable in the
  builder and save writes the JSON back to the app folder — the Builder
  `is_standard` round-trip idiom.
- The blessed release path is author → export into the app repo → git review
  → normal app release. There is no production-site export flow.
- A future code-first authoring API is another producer of the same files.
  Format stability is the only coupling.

### Visibility ladder

- Two fields on `Insights Chart v3` and `Insights Dashboard v3`:
  `visibility: Private | Specific Roles | Everyone | Public` (default
  `Private`) plus a `visible_to_roles` child table using the shared
  `Has Role` child doctype — the desk Report convention.
- The ladder is strict — each rung includes the previous. `Private` is owner
  plus person-level DocShares (DocShare is the person rung of this axis, not
  a parallel mechanism). `Specific Roles` is the desk-report pattern.
  `Everyone` is any logged-in user. `Public` absorbs `is_public`, which dies
  as a separate flag. Guest access moves inside the permission controller,
  out of the API allowlist.
- The ladder is view-only. Editing stays on the authoring axis, unchanged.
- A chart on a dashboard inherits the dashboard's audience, downward only.
  The existing linked-dashboard grant in the permission controller already
  carries this cascade. A standalone chart uses its own declaration.
- Enforcement is one seam: `frappe.has_permission`. The ladder becomes one
  grant source inside the `InsightsPermissions` controller, beside the
  existing ones. Nothing outside the controller reads the ladder.
- The `Insights User` role appears nowhere in the viewing path. Viewing
  implies no access to Insights: no role, no app access, no catalog of
  other visible content.

### Data authority

- `data_authority: Viewer | Author`, default `Viewer`, declared on the
  chart (pinned by this spec, see Further Notes). Engine-enforced at
  execution: the request names the chart, the doc names the authority, and
  no parameter on the wire can flip it. The surface — Insights app, desk
  island, public link — is irrelevant.
- Viewer mode is the engine's native permission application, safe under any
  audience.
- Author mode applies the author's permission context at execution without
  switching the session user. It is the deliberate escalation for
  whole-number content, the only meaningful mode on the `Public` rung, and
  the defined mode for non-site-DB sources.
- The authoring UI makes `Public | Everyone` + `Author` a loud explicit
  confirmation. The copy states that viewers can see the underlying rows.

### Viewer data endpoints

- A small set of endpoints serves island consumption: fetch a dashboard
  (items, layout, capability flags), fetch a chart (config), fetch chart
  data (results). Plain `frappe.whitelist()`, no role check. Each endpoint
  resolves the reference, checks read permission on the content doc through
  `frappe.has_permission`, and executes under the doc's `data_authority`.
- Capability flags in the dashboard response (can edit, can duplicate)
  drive the island's rights-gated affordances, so the client never guesses.
- Existing `insights_whitelist` endpoints stay as they are for the authoring
  app.
- Drill-down, when ticket 11 lands, re-executes the chart's query with the
  segment's filters under the chart's authority, bounded by the query's
  result columns. The endpoints never expose the query definition.

### Customization floor

- Standard content is read-only on a site. "Duplicate" is the only
  customization: a plain user copy of the content closure into a
  user-owned workbook, the same shape template import produces today.
  Duplicate requires authoring access.
- The duplicate-beside-original UX is acknowledged debt. Ticket 10 owns the
  real model. Nothing here depends on its outcome — resolution lives behind
  the resolver.

### One frappe-ui version

- The SPA build target follows framework's frappe-ui version. Framework's
  lockfile is the version authority for both build targets — the SPA
  bundles that version, the islands leave it external and get it from the
  runtime at load.
- Until framework's frappe-ui changes publish, both targets consume the
  framework checkout through a link dependency. The pinned-version
  dependency returns when the release exists.

### Migration

- The four shipped workbook templates re-export into the bundle format.
- Existing imported template copies become user documents — they were
  user-editable, so they are forks by definition.
- The gallery's "import" becomes "duplicate". The version/checksum update
  model (`imported_version`, `imported_checksum`, warn+manual) retires.
- `is_public = 1` migrates to `visibility = Public`. The public shared
  pages keep working, gated by the ladder inside the controller.
- New glossary entries land in `CONTEXT.md`: Bundle, Standard content,
  Slug.

## Testing Decisions

Good tests exercise external behavior at the seams. The seams are the ones
the decisions already name — no new ones.

- **`frappe.has_permission` (the access seam).** Matrix tests over the
  ladder: each rung × chart/dashboard × member/non-member/guest, cascade
  from dashboard to chart, `Private` DocShare behavior, and the invariant
  that no viewing path consults the `Insights User` role. Prior art: the
  existing permission tests.
- **The resolver.** Each reference form resolves to the right doc. Unknown
  reference and denied read return the same answer. A Duplicate is never
  returned for a shipped id.
- **Bundle reconcile (the sync seam).** A fixture bundle: sync creates,
  re-sync is a no-op, a changed file updates, a removed file deletes,
  uninstall deletes standard docs and spares user copies. Prior art: the
  workbook template tests.
- **Viewer endpoints.** A user inside the audience gets data with no
  Insights role. A user outside gets the denied answer. A guest gets data
  only on `Public`. `data_authority` flips row filtering between viewer and
  author context, and no request parameter can override it.
- **Island build (the build-time gate).** The two entries build as ESM with
  bare imports only from the registered runtime specifiers, within the
  budget. The lint fails a fixture that imports the router. These run in
  the build, which makes the gate itself the test.
- **Export round-trip.** Export writes files free of volatile fields, and a
  re-export after no edits is byte-identical.

## Out of Scope

- The drill-down interaction (ticket 11). The seam is reserved: segment
  click, internal to the island, rows-only semantics already fixed by
  ticket 09.
- The real customization model (ticket 10). Duplicate is the floor.
- The desk dashboard page shell itself — routes, workspace sidebar items,
  the mount call site. That is framework-side work, one mount call thin,
  written against this spec's props contract.
- The Vue-frontend-app embed UX (ticket 06).
- Migration of legacy desk `Dashboard` / `Dashboard Chart` content.
- The DuckDB store switch and framework's standard sync.
- Datasets as first-class shippable units, the code-first authoring API,
  and contextual/inline charts. All wait on this base.
- Role-based edit grants and the unified permission-rule store.
- The v16 rollout strategy beyond the flag's semantics.

## Further Notes

- **Pins made by this spec** (ambiguities in the tickets, resolved here,
  not contradictions):
  1. The desk URL pattern is deliberately left open, revising ticket 05's
     two route forms. The enabling conditions are pinned instead: every
     dashboard carries a slug, and the resolver accepts logical id, slug,
     and docname. The pattern is a one-place choice in the framework-side
     shell, and it hardens at the first release that ships dashboard
     links — not at branch merge. If a two-segment shipped route returns,
     its `<name>` is the item's logical name, never the bundle folder —
     ticket 03 made folders organization, not identity.
  2. `data_authority` lives on the chart, where execution happens. Ticket
     09 placed the visibility fields on both doctypes but left the
     authority field's home ambiguous.
  3. Standard docs attach to one site-managed workbook per bundle. Ticket
     03 kept the workbook out of the shipping format but the v3 builder is
     workbook-centric, so developer-mode iteration needs a container. The
     container is created by sync and is not part of the format. Per-bundle
     (not per-app) keeps the builder view at authoring granularity — one
     dashboard often carries five or more queries, and a per-app container
     would pile every shipped doc of a large app into one workbook.
  4. Shipped content's visibility is vendor-declared and read-only on a
     site in v1. A site that wants a different audience duplicates. This
     is a consequence of ticket 03's read-only floor meeting ticket 09's
     doc-declared ladder, stated here so it is chosen, not stumbled into.
- **Fonts.** `@font-face` is dead in adopted stylesheets. If island text
  needs a non-system font, the document must load it. For v1 the islands
  render with the host page's fonts.
- **The 2.3 MB lesson.** The measured failure was the entry linking the
  SPA router graph and the unscoped app stylesheet. The navigation seam
  and the lint exist to make that class of entry unbuildable, and the
  budget catches what they miss.
- **Filter persistence storage** is an implementation choice (client-side
  per user is acceptable for v1). The behavior — per-user, per-dashboard,
  survives reload — is the contract.
