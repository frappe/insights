# 20 — Bundle shipping and declarative reconcile

Type: task
Status: ready-for-agent
Blocked by: 19
Spec: [spec-insights-foundation.md](../spec-insights-foundation.md), "Bundle format and shipping" and "Sync: declarative reconcile"

## What to build

An app ships analytics as files, and every site that installs the app has
the content after migrate.

The format: an app ships `insights/<bundle>/` folders. Each bundle holds
typed subfolders (`query/`, `chart/`, `dashboard/`) with one JSON file per
item, named by logical name, plus a `bundle.json` (title, `required_apps`,
one integer format version). Item names are unique per app — `{app}/{name}`
is a flat namespace, bundle folders are organization, not identity. Internal
references are logical names, never docnames. The format version is owned by
Insights, append-only within a major, importers tolerate unknown keys.

The sync: bundles reconcile on `after_migrate` and `after_app_install` into
real Insights documents flagged standard, carrying their `{app}/{name}`
identity in the resolver's lookup field. Discovery walks the installed apps'
`insights/` directories — real installed apps, not a fakeable seam.
Reconcile is declarative and idempotent: new items are created, changed
items updated, removed items deleted. `before_app_uninstall` deletes the
app's standard docs. User copies survive both.

Standard docs are read-only on a site outside developer mode. Each bundle's
docs attach to one site-managed, Administrator-owned workbook per bundle,
created by sync and titled from `bundle.json` — a site-side container, not
part of the format. Shipped dashboards get their slug at sync: the logical
name, app-qualified only on collision, with a sync warning.

## Acceptance criteria

- [ ] A fixture bundle syncs on migrate: docs exist, flagged standard, with
      logical ids, attached to a per-bundle workbook
- [ ] Re-sync with no changes is a no-op, a changed file updates the doc, a
      removed file deletes it
- [ ] Uninstall deletes the app's standard docs and spares user copies
- [ ] Standard docs reject edits outside developer mode
- [ ] Internal references (dashboard→chart, chart→query) resolve through
      logical names after sync
- [ ] Shipped slugs assign at sync, app-qualified on collision with a warning
