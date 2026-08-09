# Mount and renderer API

Type: grilling
Status: resolved

## Question

The concrete API a consumer app programs against, now that the mechanism is
settled (island via `mountVueIsland`) and the ownership split is drawn.

**The mount call.** What framework's page invokes to put an Insights dashboard
or chart into an element:

- Host context in: which document, filters, theme, locale, read-only vs
  interactive.
- Events out: drill-down requests, filter changes, navigation ("open in
  Insights"), errors.
- Lifecycle: teardown, re-mount, loading and error states.
- `mountVueIsland` gaps ticket 02 found: no app-config hook, `<link>` per
  shadow root.

**Identity.** How an app references a chart or dashboard so the reference
survives export, import, and rename — and how the chart→query reference stays
stable and addressable (the datasets-later constraint).

**The renderer toggle.** Framework's page decides Insights vs legacy from three
conditions: is Insights installed, is the feature flag on, is this document an
Insights dashboard or a legacy `Dashboard`. Settle where that lives, how apps
opt in, and how it retires.

Resolves into the shape a spec can be written from.

## Answer

**Discovery: a hook-declared island registry.** Apps declare mountable
islands in `hooks.py` — `ui_islands = {"insights.dashboard":
"insights_dashboard.bundle", "insights.chart": "insights_chart.bundle"}`
— and framework exposes one generic call:
`frappe.ui.mount_island(name, el, context)`, resolving name → assets.json
→ dynamic `import()` → the module's `mount`. The registry, not the
Insights wiring, is the platform feature; the next app that wants a
desk-mountable surface gets the same foundation. The term is **island**,
resolved now because it is about to be cast into hook keys and API names:
it names the isolation property the contract actually guarantees, and it
is the only candidate with a clean namespace on both sides (widget, block,
view, page all collide in desk; embed already means Insights' public
iframe sharing). Recorded in `CONTEXT.md`.

**The mount envelope is structured, with ownership per compartment.**
`mount(el, { host, props, on }) → { update(props), unmount() }`:

- `host` — framework-injected ambient context, identical for every
  island, never assembled by the caller: theme (live), locale/timezone,
  current user, base URL. Dark mode and translations are a platform
  guarantee, not a per-island prop.
- `props` — island-specific, opaque to framework. For
  `insights.dashboard`: the dashboard reference, initial filter state,
  read-only vs interactive.
- `on` — island-specific callbacks: `onError` (notification, not
  delegation — the island renders its own error and loading states),
  `onNavigate` ("open in Insights"), filter-change notifications.
  Drill-down stays internal to the island.

`update(props)` pushes new props without a re-mount; teardown stays
idempotent per `mountVueIsland`'s existing behavior. `mountVueIsland`
grows a `configure(app)` option so an island registers its plugins and
global components at app creation — deleting ticket 02's `IslandBoot`
workaround. The `<link>`-per-root gap is already closed by the build
ticket's `adoptedStyleSheets` decision.

**Identity: logical ids, resolved by Insights at mount.** Two forms, one
resolver: shipped content is referenced as `{app}/{name}` (e.g.
`crm/pipeline-overview`), the template-id convention extended to runtime
references, resolved to the site-local copy via the `from_template`-style
lookup; site-local content a user wired up themselves may use the plain
docname. Hash docnames never cross the contract boundary — consumer apps
only ever ship logical ids. This keeps a later doctype-naming change
(hash → readable slugs) Insights-internal: the resolver changes, no
consumer notices. Which copy wins on a fork (pristine vs customized) is
resolution policy owned by the content-lifecycle ticket. One level down,
a chart references its query by name inside Insights' documents — the
mount API never flattens a chart into inline query config — which keeps
queries addressable for the datasets-later promotion.

**The renderer toggle is one framework-owned bridge.** A single resolver
(e.g. `frappe.ui.get_dashboard_renderer(doc)`) holds all three conditions
— Insights installed, site flag on, referenced document is Insights
content vs legacy `Dashboard` — and pages branch once on its answer. The
flag gates rendering surfaces, not content: Insights dashboards work at
`/insights` regardless. Insights never participates — it registers its
islands unconditionally and contains zero fallback awareness — so the
bridge retires (v17: body becomes one line, then deleted with its call
sites) without an Insights release.
