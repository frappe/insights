# 12 — Repoint the SPA at framework's frappe-ui

Type: task
Status: ready-for-agent
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

- [ ] The frontend consumes frappe-ui from the framework checkout through a
      link dependency, with a note recording that the pinned version returns
      when framework's frappe-ui release exists
- [ ] The production build succeeds with one frappe-ui in the graph
- [ ] The SPA works on the test site: login, open a workbook, run a query,
      render a chart and a dashboard
- [ ] The dev server works
