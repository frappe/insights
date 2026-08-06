# 12 — Repoint the SPA at framework's frappe-ui

Type: task
Status: resolved
Blocked by: none — can start immediately
Spec: [spec-insights-foundation.md](../spec-insights-foundation.md), "One frappe-ui version"

## What to build

The standalone SPA at `/insights` builds and runs against the framework
checkout's frappe-ui copy instead of its own pinned version. Framework's
lockfile becomes the version authority for both Insights build targets. Until
framework's frappe-ui changes publish to npm, the dependency is a link to the
framework checkout (branch `desk-islands` under the framework app).

The framework copy is newer than the version the SPA pins today, so this
ticket absorbs any breakage the bump surfaces.

## Acceptance criteria

- [x] The frontend consumes frappe-ui from the framework checkout through a
      link dependency, with a note recording that the pinned version returns
      when framework's frappe-ui release exists
- [x] The production build succeeds with one frappe-ui in the graph
- [x] The SPA works on the test site: login, open a workbook, run a query,
      render a chart and a dashboard
- [x] The dev server works

## Comments

2026-08-05 — done. `frontend/package.json` now reads
`"frappe-ui": "link:../../frappe/frappe-ui"`, which is the framework
checkout on branch `desk-islands` (1.0.0-beta.30, tip `911024a65`). The
pinned `^1.0.0-beta.24` returns as soon as framework's frappe-ui publishes
a release — at that point the link, the `resolve.dedupe` list in
`vite.config.js`, and the `frappe-ui > ` prefix on the tiptap pre-bundle
list all go back to their plain forms.

The linked package carries its own `node_modules`, which is what the two
vite changes are for. `resolve.dedupe` keeps `vue`, `vue-router`,
`@headlessui/vue`, `@vueuse/core` and `dayjs` to one copy — vue-router in
particular was landing in the bundle twice, which breaks every frappe-ui
component that resolves a route. The tiptap ids are resolved through
`frappe-ui` so the pre-bundle covers the copy frappe-ui actually imports.

Also dropped the `reka-ui: 2.5.0` resolution. It only ever existed to pin a
frappe-ui transitive dependency, and framework's lockfile owns that now —
frappe-ui reads reka-ui 2.9.9 from its own tree either way.

No `src2` change was needed. The breaking changes in the beta.24 → beta.30
range are all in the selection family (`displayValue`, `clearSelection`,
`clearAll`, `compareFn`, `slotName`, `#option`, `allowCustomValue`) and
Insights uses none of them.
