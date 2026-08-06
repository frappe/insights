# Spec: foundation-branch reshape — the workbook as shipping unit

Status: ready-for-agent
Target: the Insights foundation branch (built from
[spec-insights-foundation.md](spec-insights-foundation.md)), rebased on
`develop`.

This spec turns the second-wave decisions into the refactor they gate. It
amends [spec-insights-foundation.md](spec-insights-foundation.md) where the
two conflict — see Further Notes for the superseded pins.

Sources: the resolved tickets
[24](issues/24-shipping-unit-bundle-or-workbook.md) (shipping unit),
[25](issues/25-workbook-item-list-model.md) (item lists),
[26](issues/26-viewer-seat-role.md) (viewer seat).
Glossary: `CONTEXT.md` — Standard workbook, Standard content, and Standard ID
are ratified terms; "Bundle" and "logical id" are retired.

## Problem Statement

The foundation branch proved the contract, but it speaks a vocabulary the
second wave retired. Sync invents an Administrator-owned container workbook
per bundle and remembers it in a site global, with grep-the-defaults discovery
and hand-rolled garbage collection — a workbook in everything but identity.
The identity field is named `logical_id`, a name that says what it is not.
The shipping format is append-only once an app ships content against it, so
`bundle.json` must become `workbook.json` before that happens — this is the
one change with a freezing deadline. And the permission controller enforces a
model that is stated nowhere, so every new grant source is negotiated against
folklore.

## Solution

The shipping unit is the workbook. The manifest becomes the workbook's file,
`Insights Workbook` carries the same identity pair as the content doctypes,
and sync reconciles it as the fourth doctype — the container machinery and
its site global die. `logical_id` renames to `standard_id` everywhere. A
standard workbook admits only standard items, so reconcile-deletion needs no
orphan handling. No identifier keeps "bundle". The permission controller gets
its model written down as the grant-source table; its behavior does not
change.

## User Stories

1. As an app developer, I want my shipped folder to be a workbook with a `workbook.json`, so that the file I edit and the thing users see are one concept.
2. As an app developer, I want the folder name to be the workbook's Standard ID, so that identity is visible in my repo layout and never invented site-side.
3. As an app developer, I want renaming a shipped item or folder to be understood as delete-and-create, so that identity rules are uniform and never surprising.
4. As a site user, I want shipped workbooks read-only like their contents, so that standard content is one consistent read-only surface.
5. As a site user, I want my own work kept out of shipped workbooks, so that an app update can never delete or orphan anything of mine.
6. As a site administrator, I want app uninstall and content removal to clean up their workbooks completely, so that nothing standard lingers or leaks.
7. As an Insights developer, I want one identity field named `standard_id` on all four doctypes, so that the name states the rule: only standard content has one.
8. As an Insights developer, I want the permission controller's grant sources stated as a table in its docstring, so that a new source must earn a row, not a join.

## Implementation Decisions

### Format: `workbook.json`

- The manifest file renames from `bundle.json` to `workbook.json`. Same three
  keys: `title`, `required_apps`, `format_version`. `title` is the workbook's
  shipped field; the other two are shipping metadata that ride in the file
  and never land on the document.
- Discovery recognizes `workbook.json` only. There is no `bundle.json`
  compatibility read — nothing has shipped against the format, and this
  refactor is why nothing may until it lands.
- `FORMAT_VERSION` stays 1. Nothing else enters the format now; folders,
  ordering, and layout are append-only additions if demand shows.
- The four folders Insights ships (`insights/insights/erpnext_*`) rename
  their manifests in the same change.

### Identity: `standard_id` on four doctypes

- `logical_id` renames to `standard_id` on `Insights Query v3`,
  `Insights Chart v3`, and `Insights Dashboard v3` — doctype JSON, all code,
  all tests, all frontend usage. A guarded `rename_field` patch migrates
  existing columns (only developer benches carry the old field).
- `Insights Workbook` gains `standard_id` and `is_standard`. Its Standard ID
  is `{app}/{folder}` — the folder name is identity now, so renaming a
  shipped folder deletes one workbook and creates another, the same event as
  renaming any shipped item. Item names stay flat per app; the folder still
  does not namespace them.
- The term is "Standard ID" in prose and docstrings, `standard_id` in code.
  "Logical name" remains the word for the bare `{name}` inside a shipped
  folder's files.

### Sync: the workbook is the fourth reconciled doctype

- Reconcile order: workbook first, then queries, charts, dashboards.
  Deletion reverses it, so the workbook goes last and always empty.
- The workbook reconciles like any item: created with `standard_id`,
  `is_standard`, and the manifest's title; retitled when the manifest
  changes; deleted when the folder no longer ships (or `required_apps` stops
  being satisfied). Owner is Administrator, as for all standard content.
- `_container_workbook`, `_containers_of`, `_cleanup_containers`, and the
  `insights_bundle_workbook:<key>` site global die. A patch migrates each
  existing global into `standard_id` + `is_standard` on its workbook, then
  clears the globals. The patch runs before the first sync on migrate.
- `standard_content()` (the gallery feed) groups by the workbook's
  `standard_id` and reads its title directly — no DefaultValue grep.

### Guards: standard workbooks admit only standard items

- `block_standard_edits` / `block_standard_deletes` hook `Insights Workbook`
  like the content doctypes: read-only on a site, editable on a
  developer-mode bench, writable by sync.
- New membership guard, hooked on the three content doctypes and
  `Insights Folder`: a document whose `workbook` is a standard workbook must
  itself be standard content written by sync. Anything else — a user query,
  a folder, a moved item — is blocked with a message pointing at Duplicate.
  This is what makes reconcile-deletion ordinary: the branch where a site
  put its own work into a shipped container cannot arise.
- The ratified invariant, maintained by sync and asserted by the guard:
  an item's `is_standard` equals its workbook's. `is_standard` stays stored
  on items — it is load-bearing in DB filters, and sync is its only writer.

### Vocabulary: no identifier keeps "bundle"

- `insights/bundles.py` → `insights/standard_content.py` — it is the
  standard-content module: sync, the gallery feed, and the guards for all
  four doctypes. `insights/api/bundles.py` → `insights/api/standard_content.py`,
  with frontend call sites updated.
- The dataclasses and functions rename to match the glossary:
  `Bundle` → `ShippedWorkbook`, `BundleItem` → `ShippedItem`,
  `BundleError` → `StandardContentError`, `sync_bundles` →
  `sync_standard_content`, `duplicate_bundle` → `duplicate_workbook`.
  `insights/bundle_export.py` → `insights/export_to_app.py`. Hooks entries,
  `migrate.py`, and patches follow. Exact names beyond these are the
  refactor's business; the rule is that no identifier, docstring, comment,
  test name, or frontend type keeps "bundle".
- Frontend: `export_targets.ts` types and the Library components rename
  their bundle-shaped props to workbook terms. User-facing strings already
  never said bundle; they do not change.

### The permission controller's named model

- No behavior change. The reshape writes the model down and names the seam:
- The grant-source table from ticket 26 becomes the `permissions.py` module
  docstring — ownership, DocShare, container inheritance, team resource
  grants, audience ladder, and the seat, each with its doctypes and actions.
  The stated rule: a new grant source must earn a row in this table before
  it earns a join in this file.
- `check_app_permission`'s docstring states its contract: the authoring
  gate — "may this person enter the builder" — never consulted for viewing.
- `can_edit` in `api/viewer.py` is already the single seat-AND-rights
  helper; it stays the only place the conjunction is assembled.

## Testing Decisions

The seams are unchanged; the suites rename with the code and grow four cases.

- **Workbook reconcile.** In the fixture app: first sync creates the
  workbook with `standard_id`, `is_standard`, and the manifest title; a
  retitled manifest retitles it; re-sync is a no-op; removing the folder (or
  breaking `required_apps`) deletes the workbook and everything in it, in
  order; uninstall does the same.
- **Membership guard.** Creating a user query in a standard workbook throws;
  so does creating an `Insights Folder` there and moving an existing item
  in. Duplicate still lands in a user workbook untouched.
- **Identity migration.** The patch turns a seeded
  `insights_bundle_workbook:<key>` global into `standard_id`/`is_standard`
  on the workbook and clears the global; a second run is a no-op.
- **Rename completeness.** The existing bundle/resolver/viewer/export suites
  pass under the new names, with fixtures shipping `workbook.json`. A grep
  gate in the test suite asserts no `logical_id` and no `bundle` identifier
  survives in `insights/` or `frontend/src2/` (allowing the glossary's
  "_Avoid_: bundle" entries and patch filenames).

## Out of Scope

- The client-side residue of the stored-list model (title mirror, index
  routes) — handed to the workbook-state-model effort by ticket 25, spun
  off separately.
- Retiring team resource grants on content doctypes — recorded as an input
  to the parked unified-permission-store effort by ticket 26.
- Tickets [06](issues/06-vue-app-embed-ux.md),
  [10](issues/10-site-customization-of-shipped-content.md), and
  [11](issues/11-drill-down-interaction.md).
- Any format addition beyond the manifest rename (shipped folders, ordering,
  layout).

## Further Notes

- **Supersedes** spec-insights-foundation pin 3 (one site-managed container
  workbook per bundle, tracked in a site global): the container is now the
  shipped workbook itself, with identity, at the same per-folder
  granularity. The other foundation pins stand.
- **Amends** ticket 04's vocabulary: references are Standard IDs. The
  resolver's accepted forms (Standard ID, slug, docname) and its
  deny-equals-missing behavior are unchanged.
- **The freezing deadline** is the reason this reshape precedes further
  feature work: `workbook.json` and `{app}/{folder}` identity must be the
  format's first public shape. Until this lands, no app may ship content
  against the branch.
- **Folder renames after release** are delete-and-create by design. If
  demand shows, a `renamed_from` alias is the deferred mechanism, for
  folders and items alike (ticket 03's position, unchanged).
