# Build ownership and island preset

Type: grilling
Status: open

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
