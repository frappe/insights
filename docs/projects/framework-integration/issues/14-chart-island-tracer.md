# 14 — Tracer bullet: a minimal `insights.chart` island

Type: task
Status: ready-for-agent
Blocked by: 12, 13
Spec: [spec-insights-foundation.md](../spec-insights-foundation.md), "Island entries and router decoupling"

## What to build

The first end-to-end island. A second Vite build target builds an
`insights.chart` entry with framework's island preset (`@framework/ui/vite/island`,
consumed from the framework checkout on branch `desk-islands`). The entry
exports the mount contract — `mount(el, { host, props, on })` returning
`{ update, unmount }` — and uses `configure(app)` for the plugins the viewer
graph needs. `hooks.py` declares the island under `ui_islands`. Registration
is unconditional: no flag check, no fallback awareness.

Mounted on a desk page through `frappe.ui.mount_island` (the framework
`desk-islands` branch provides the loader), the island renders a chart by
docname for a user who already has access. Viewer endpoints and audience
enforcement come later — the demo user is an authorized Insights user.

Known constraints from the framework contract: bare imports are limited to
the runtime-registered specifiers, everything else bundles and counts against
the size budget. Dark mode requires a `data-theme` attribute on a container
inside the shadow root, updated live from `host.theme`. `@font-face` is dead
in adopted stylesheets — the island renders with the host page's fonts.

## Acceptance criteria

- [ ] The island build emits ESM assets with `.island.js` / `.island.css`
      keys registered in assets.json
- [ ] `ui_islands` declares `insights.chart`
- [ ] The built entry's bare imports are limited to runtime-registered
      specifiers, and the build passes the size budget
- [ ] The chart renders inside a shadow root on a desk page on the test site
- [ ] The island follows a mid-session theme switch through `host.theme`
- [ ] `update(props)` re-renders without a re-mount, and `unmount` is
      idempotent
- [ ] The SPA build target still builds and works unchanged
