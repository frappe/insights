# Build ownership and island preset

Type: grilling
Status: resolved

## Question

Who builds a mountable island, and what does framework supply to make it
uniform?

Inputs from ticket 07: the externals set is the whole runtime closure,
resolved at build time against framework's installed node_modules; the
runtime artifact itself does not exist yet (the POC builds self-contained
IIFEs) and shipping it is a framework deliverable settled here; both
Insights build targets (standalone SPA and island) consume framework's
frappe-ui copy, so Insights carries no closure pins of its own.

- Who runs the build. Apps own their island builds (framework's builder
  globs only its own `islands/` directory) — or framework builds consumer
  islands too, which closes the stale-island hole (`bench build --apps
  frappe` rebuilding the runtime under an already-built island). Left open
  by ticket 07; the person driving this map can make framework-side calls.
- What framework publishes to make builds uniform: a Vite preset carrying
  the shared CSS treatment (`:root`→`:host` token rewrite, Tailwind config,
  lib output, CSS extraction) and the runtime externals.
- The runtime artifact: what it exports, how a page loads it, how the
  standalone SPA consumes the same frappe-ui copy.
- Where does built output land, and how does the desk page resolve it —
  `frappe.require` plus assets.json, or absolute `/assets/...` paths (which
  `bundled_asset` already passes through)?
- Dev and watch story for an app iterating on its island.
- **The entry-boundary rule.** Ticket 02 measured a chart-only island at 2.3 MB
  of JS because `charts/chart.ts` imports `../router`, and 4.8 MB of CSS
  because the stylesheet is the whole app's. What may a desk-mountable entry
  import, how is that enforced, and what is the size budget?
- Stylesheet delivery: `adoptedStyleSheets` shared across shadow roots rather
  than a `<link>` per root.

## Answer

**Apps own their island builds; framework publishes the preset and the
runtime.** `bench build` already distributes build work per app, and a
universal framework builder would make every consumer app's dependency
graph a framework build problem. Freeze-per-major removed the one real
argument for central builds: with true externals an island links to the
runtime at page load, so a stale island is old-but-compatible, not broken.

**Islands link to the runtime through an import map, as native ESM.** Desk
emits an import map in the page head — `vue`, `vue-router`, `frappe-ui`,
`echarts`, … mapped to hashed runtime files, generated from assets.json at
render — and loads islands via dynamic `import()` instead of
`frappe.require`. The consumer contract is one line in any bundler: build
ESM, leave the closure as bare imports. Runtime packages become separate
hashed files, individually cacheable. This is also the convergence path
from the runtime-version-policy ticket: a Vue-frontend app that later
wants framework's runtime adopts the same map. Desk changes are
framework-side; the legacy esbuild pipeline is untouched and classic
bundles coexist with module islands on the same page. Island output stays
in `sites/assets/<app>/dist`, registered in assets.json.

**The generic enforcement is a size budget, not import rules.** What
counts as "the SPA graph" is app-local knowledge, so the preset ships a
per-entry size gate (budget set from the first clean measured build plus
slack — the 2.3 MB figure came from a coupled entry no one should build
again). The import-boundary lint that names the offending chain is an
app-local aid; the preset may expose a `forbiddenImports` slot, but the
budget is the contract. Insights adds its own boundary lint as part of
decoupling `charts/chart.ts`-style modules from the router.

**CSS splits along the same line as the JS.** Framework builds one runtime
CSS artifact — preflight, `:host`-rewritten design tokens, and every
utility frappe-ui's own source uses — and `mountVueIsland` applies it to
each island's shadow root as a shared constructable stylesheet
(`adoptedStyleSheets`): fetched once, parsed once, one sheet object across
all roots. An island's own CSS shrinks to the utilities its templates use
(the preset's Tailwind config scans app source only) and is adopted after
the runtime sheet so app styles win ties. The runtime CSS is part of the
append-only surface: restyling mid-major is fine, removing tokens or
classes is a breaking change.

**Dev loop: preset watch mode + `hot_update` soft re-mount.** Output lands
in `sites/assets` as normal; frappe's existing build events re-run the
mount, which `mountVueIsland`'s teardown already makes safe. This is the
house pattern (Studio's disk→DB→editor sync in frappe/studio#197 rides the
same watch-plus-realtime shape). Vite dev-server HMR stays a purely
additive, app-local upgrade — a dev-only import map override touches no
contract surface.

**Framework deliverables out of this ticket:** the runtime JS artifact
(the closure as hashed ESM files), the runtime CSS artifact, the import
map emitted by desk, the module island loader, and the npm-installable
Vite preset (externals, `:root`→`:host`, Tailwind config, ESM/CSS output,
assets.json registration, size gate, watch mode).
