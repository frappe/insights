# Build ownership and island preset

Type: grilling
Status: open
Blocked by: 07

## Question

Who builds a mountable island, and what does framework supply to make it
uniform?

- Apps own their island builds (framework's builder globs only its own
  `islands/` directory, and frappe cannot resolve every consumer app's
  dependency graph) — confirm, and settle what framework publishes instead: a
  Vite preset carrying the shared CSS treatment (`:root`→`:host` token
  rewrite, Tailwind config, lib output, CSS extraction) and the externals set
  from ticket 07.
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
