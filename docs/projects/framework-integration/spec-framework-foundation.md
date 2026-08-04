# Spec: framework-side island foundation

Status: ready-for-agent
Target: `apps/frappe`, framework v16, behind a site flag.

This spec covers only the framework-side deliverables. The Insights-side work
waits on tickets [03](issues/03-content-lifecycle.md) and
[09](issues/09-desk-data-access.md) and gets its own spec.

Sources: [map.md](map.md) and the resolved tickets
[02](issues/02-rendering-isolation-mechanism.md),
[04](issues/04-v1-contract-surface.md),
[07](issues/07-runtime-version-policy.md),
[08](issues/08-build-ownership-and-preset.md).
Glossary: `CONTEXT.md` in the Insights repo ("Island" is the ratified term).

## Problem Statement

Insights must render its dashboards and charts inside desk pages. Desk has no
supported way to mount Vue + frappe-ui UI from any app. The vue-islands POC
(branch `frappe-ui-desk-poc`, PR frappe/frappe#39773) proves the mechanism —
shadow-root isolation works — but it is parked and not shippable. It builds
each island as a self-contained IIFE with Vue and frappe-ui bundled in. It
injects a stylesheet `<link>` into every shadow root, so each root parses the
full sheet again. Its builder only globs framework's own islands directory, so
no other app can ship an island. Its mount helper creates the Vue app
internally, so a page cannot register plugins or global components. Framework
`develop` does not even depend on frappe-ui. Until framework ships a real
foundation — a shared runtime, a mount contract, and build tooling — no app can
ship a desk-mountable UI unit.

## Solution

Framework ships the island foundation. It builds the runtime closure — Vue,
vue-router, frappe-ui, and frappe-ui's whole dependency tree — from its own
lockfile into hashed ESM files, plus one shared runtime CSS artifact. Desk
emits an import map, so islands link to the runtime through bare imports. Any
app declares islands through a `ui_islands` hook and builds them with a
framework-published, npm-installable Vite preset. Desk mounts an island with
one generic call, `frappe.ui.mount_island(name, el, context)`, into a shadow
root. A framework-owned renderer bridge decides Insights versus legacy
rendering per document, behind a site flag that gates rendering surfaces only.
Within a framework major the runtime surface is append-only, CSS included, so
a built island stays compatible until the next major.

## User Stories

1. As an app developer, I want to declare a mountable island in `hooks.py`, so that desk discovers it without framework code changes.
2. As an app developer, I want one generic mount call, so that I write no per-app mount plumbing.
3. As an app developer, I want framework to inject ambient host context (theme, locale, timezone, user, base URL), so that my island honors dark mode and translations without per-island wiring.
4. As an app developer, I want live theme updates in the host context, so that my island follows a mid-session dark-mode switch.
5. As an app developer, I want to pass island-specific props, so that the host page configures my island without framework knowing the shape.
6. As an app developer, I want island-specific callbacks, so that the host page reacts to navigation, errors, and filter changes.
7. As an app developer, I want my island to own its loading and error states, so that the host page never reimplements them.
8. As an app developer, I want an `update(props)` handle, so that I push new props without a re-mount.
9. As an app developer, I want idempotent unmount, so that teardown and re-mount stay safe in any order.
10. As an app developer, I want a `configure(app)` option, so that my island registers plugins and global components at Vue app creation.
11. As an app developer, I want an npm-installable Vite preset, so that my island build matches the contract with minimal config.
12. As an app developer, I want the preset to externalize the runtime closure, so that my island stays small and never double-loads Vue.
13. As an app developer, I want the preset to scope Tailwind scanning to my app source, so that my island CSS contains only the utilities my templates use.
14. As an app developer, I want the preset to rewrite `:root` tokens to `:host`, so that design tokens resolve inside a shadow root.
15. As an app developer, I want the preset to register output in assets.json, so that the loader resolves my island without manual wiring.
16. As an app developer, I want a per-entry size budget that fails the build, so that a coupled entry graph surfaces at build time, not at page load.
17. As an app developer, I want preset watch mode with a soft re-mount on `hot_update`, so that I see island changes without a full page reload.
18. As a desk user, I want islands and classic desk bundles on the same page, so that existing desk features keep working during the transition.
19. As a desk user, I want island overlays to cover desk chrome, so that drill-down dialogs and popovers feel native.
20. As a desk user, I want pages without islands to load no runtime, so that the foundation costs nothing where it is unused.
21. As a framework maintainer, I want one lockfile as the version authority for the whole closure, so that two runtime versions never meet on a page.
22. As a framework maintainer, I want the runtime surface append-only within a major, so that a stale island is old-but-compatible, never broken.
23. As a framework maintainer, I want runtime packages as separate hashed ESM files, so that each package caches independently across releases.
24. As a framework maintainer, I want the import map generated from assets.json at render, so that hashed filenames never appear in templates.
25. As a framework maintainer, I want one shared constructable stylesheet across all shadow roots, so that runtime CSS is fetched and parsed once per page.
26. As a framework maintainer, I want the legacy esbuild pipeline untouched, so that classic bundles build exactly as before.
27. As a framework maintainer, I want the renderer bridge to hold every fallback condition, so that it retires without a consumer release.
28. As a site administrator, I want a site flag that gates rendering surfaces only, so that I control rollout without touching content.
29. As an Insights developer, I want to register islands unconditionally with zero fallback awareness, so that the bridge retires without an Insights release.
30. As an Insights developer, I want to build against the runtime as bare imports, so that both my build targets follow framework's frappe-ui version.
31. As a developer of any next app, I want the registry and preset to be generic, so that my desk-mountable surface rides the same foundation.

## Implementation Decisions

### Runtime JS artifact

- The closure is Vue, vue-router, frappe-ui, and everything frappe-ui drags in
  (echarts, reka-ui, all of it). No package is negotiated individually.
- Framework's lockfile is the sole version authority. Framework `develop` gains
  a real frappe-ui dependency (the POC used a gitignored `link:`).
- Output is native ESM, one hashed file per package, registered in assets.json.
  Each package caches independently.
- The runtime loads on demand, only where an island mounts. The rule is "at
  most one framework runtime per page", in desk and Vue-frontend apps alike. A
  host app's own bundled Vue is untouched — the shadow boundary keeps them
  apart.
- Freeze-per-major: within a framework major the runtime surface is
  append-only. Patch and extend, never break. Breaking bumps ride framework
  majors.

### Runtime CSS artifact

- One artifact: preflight, `:host`-rewritten design tokens, and every utility
  frappe-ui's own source uses.
- Delivery is a shared constructable stylesheet. The mount helper adopts it
  into each island's shadow root via `adoptedStyleSheets` — fetched once,
  parsed once, one sheet object across all roots. Never a `<link>` per root.
- An island's own sheet is adopted after the runtime sheet, so app styles win
  ties.
- The CSS is part of the append-only surface. Restyling mid-major is fine.
  Removing tokens or classes is a breaking change.

### Import map

- Desk emits an import map in the page head at render, generated from
  assets.json. It maps each bare specifier in the closure (`vue`,
  `vue-router`, `frappe-ui`, `echarts`, …) to its hashed runtime file.
- This is the convergence path for Vue-frontend apps: a host app that later
  wants framework's runtime adopts the same map. That adoption is direction,
  not a deliverable here.

### Island loader and `ui_islands` registry

- Apps declare islands in `hooks.py`:
  `ui_islands = {"insights.dashboard": "<asset key>", "insights.chart": "<asset key>"}`.
- `frappe.ui.mount_island(name, el, context)` resolves name → hook registry →
  assets.json → dynamic `import()` → the module's `mount`. No `frappe.require`.
- Pinned by this spec: island asset keys use a form distinct from the legacy
  `.bundle.js` keys (for example `.island.js`), so the module loader and the
  classic loader never claim the same asset.
- The legacy esbuild pipeline is untouched. Classic bundles and module islands
  coexist on one page.

### Mount envelope

The shape, from the grilling ticket:

```
mount(el, { host, props, on }) → { update(props), unmount() }
```

- `host` — framework-injected ambient context, identical for every island:
  theme (live), locale, timezone, current user, base URL. The caller never
  assembles it.
- `props` — island-specific, opaque to framework.
- `on` — island-specific callbacks. `onError` is a notification, not a
  delegation — the island renders its own error and loading states.
  `onNavigate` carries "open in Insights"-class intents. Drill-down stays
  internal to the island.
- Pinned by this spec: the `context` argument of `mount_island` is
  `{ props, on }` only. Framework injects `host` before it reaches the island.
- `update(props)` pushes new props without a re-mount. Teardown stays
  idempotent.
- `mountVueIsland` grows a `configure(app)` option, called at Vue app creation
  for plugins and global components.

### Renderer bridge

- One framework-owned resolver, for example
  `frappe.ui.get_dashboard_renderer(doc)`, holds all three conditions: Insights
  installed, site flag on, document is Insights content versus legacy
  `Dashboard`. Pages branch once on its answer.
- The flag gates rendering surfaces, not content. Insights dashboards work at
  `/insights` regardless of the flag.
- Consumer apps never see the conditions. Retirement path: in v17 the body
  becomes one line, then the bridge is deleted with its call sites — no
  Insights release required.

### Vite preset

- Published as an npm package. It carries: the runtime externals, the
  `:root`→`:host` token rewrite, a Tailwind config scanning app source only,
  ESM output with extracted CSS, output into the app's standard built-assets
  directory, and assets.json registration.
- Per-entry size-budget gate: the budget comes from the first clean measured
  build plus slack, and an over-budget entry fails the build. This is the
  contract-level enforcement. An optional `forbiddenImports` slot may exist,
  but import-boundary lint is app-local, not the contract.
- Watch mode: output lands in built assets as normal, framework's existing
  build events fire `hot_update`, and the page soft re-mounts the island
  (safe because teardown is idempotent). Vite dev-server HMR stays an
  app-local, dev-only upgrade via an import map override — it touches no
  contract surface.

### Changes versus the POC

The POC branch `frappe-ui-desk-poc` is the reference implementation. What
changes:

| POC | This spec |
| --- | --- |
| Islands are self-contained IIFEs (`esbuild/build-islands.mjs`) | Islands are ESM with the closure as bare imports, built by each app with the preset |
| Vue and frappe-ui bundled into every island | One shared runtime artifact, linked through the import map |
| Stylesheet `<link>` injected per shadow root | One shared constructable stylesheet via `adoptedStyleSheets` |
| `mountVueIsland` (`frappe/public/js/frappe/ui/vue_island.js`) has no app-config hook | `configure(app)` option |
| Builder globs framework's islands directory only | `ui_islands` hook registry, any app ships islands |
| Loaded as script bundles | Loaded via dynamic `import()` through `frappe.ui.mount_island` |

The POC's shadow-root isolation and idempotent teardown carry over unchanged.

## Testing Decisions

Good tests exercise external behavior at the seams. The seams are the ones the
ownership split already names — no new ones.

- **`frappe.ui.mount_island` (the primary seam).** Test with a fixture island,
  never with Insights. Assert: resolution through hook registry and
  assets.json, mount into a shadow root, `host` injected, `update(props)`
  without re-mount, idempotent unmount, `configure(app)` called at creation,
  a useful error for an unknown island name, the runtime sheet is one shared
  object across two mounted roots, and a classic bundle on the same page keeps
  working.
- **The preset (the build-time seam).** Build a fixture entry and assert: ESM
  output with the closure left as bare imports, CSS holds only the fixture's
  utilities, tokens are `:host`-scoped, assets.json is registered, and an
  over-budget entry fails the build.
- **The renderer bridge.** Cover the condition table: each combination of
  installed/flag/document-type yields the right renderer, and flipping the
  flag changes surfaces without touching content.
- **The import map.** A rendered desk page head carries a map whose entries
  match assets.json hashes.

Prior art: framework's Cypress suite for the page-level assertions, and plain
node-level tests against fixtures for the preset. Follow whichever pattern the
neighboring framework tests already use.

## Out of Scope

- Everything Insights-side: the island entries themselves, decoupling chart
  entries from the router, Insights' own boundary lint, repointing the
  standalone SPA at framework's frappe-ui copy, and the logical-id resolver.
  These wait on tickets 03 and 09.
- Vue-frontend host apps externalizing their own runtime against framework's.
  Recorded as direction only.
- The desk dashboard page UX (ticket 05) and the Vue-app embed UX (ticket 06).
- Migration of legacy `Dashboard` / `Dashboard Chart` content.
- The DuckDB store switch and framework's standard sync.
- The v16 rollout strategy beyond the flag's semantics.

## Further Notes

- **frappe-ui prerequisite PR.** The POC's linked frappe-ui checkout (branch
  `frappe-ui-desk-poc`, based on beta.29) carries three commits that must land
  upstream before islands work without a `link:` dependency. One: the
  `usePortalTarget` inject composable — a host-level portal default wired into
  the overlay components, with precedence explicit `portalTo` prop > host
  inject > reka-ui default. Main only has the per-component `portalTo` prop,
  which does not cover the island case (the mount helper sets one target per
  shadow root, islands pass nothing). Two: the companion fix that applies the
  target in popover and timepicker. Three: the lucide icons Vite plugin
  extracted to its own export — the preset imports it, and main only ships the
  combined module. Until this PR merges and releases, the framework branch
  keeps the `link:` checkout arrangement.
- **Two known POC build bugs** for whoever touches the legacy pipeline:
  `autoprefixer` is required but undeclared in framework's `package.json`, and
  the `production` script's argument ordering makes `bench build --app X`
  silently build every app.
- **Size-budget context.** The cautionary number: a chart-only island with the
  runtime externalized still measured 2.3 MB of JS and 4.8 MB of CSS, because
  the entry linked the SPA's router graph and the unscoped app stylesheet.
  The budget exists to catch exactly that class of entry.
- **Pins made by this spec** (ambiguities in the tickets, resolved here, not
  contradictions): the island asset-key form is distinct from legacy
  `.bundle.js` keys, and the caller's `context` is `{ props, on }` with `host`
  framework-injected.
