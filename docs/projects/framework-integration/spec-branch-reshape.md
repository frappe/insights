# Spec: foundation-branch reshape — the workbook as shipping unit

Status: shipped 2026-08-07, in six commits:
`f73cf967` the manifest rename, `7e467107` the workbook as fourth reconciled
doctype, `18ae4068` the membership guard, `557671c1` `standard_id`,
`bb936049` the permission docstring, `08592f36` the vocabulary. Two follow-ons
the work itself raised: `e100ad99` the grep gate, `9cf21466` the manifest
write-back.
Re-specced: 2026-08-07, against two rounds of work that landed while this spec
waited — [spec-one-renderer.md](spec-one-renderer.md) in full, then a sync-race
fix and an `is_public` retirement. Both rounds shrank this reshape. See Further
Notes.
Target: the Insights foundation branch (built from
[spec-insights-foundation.md](spec-insights-foundation.md)), rebased on
`develop`, with one-renderer's five steps already in it.

This spec turns the second-wave decisions into the refactor they gate. It
amends [spec-insights-foundation.md](spec-insights-foundation.md) where the
two conflict — see Further Notes for the superseded pins.

Sources: the resolved tickets
[24](issues/resolved/24-shipping-unit-bundle-or-workbook.md) (shipping unit),
[25](issues/resolved/25-workbook-item-list-model.md) (item lists),
[26](issues/resolved/26-viewer-seat-role.md) (viewer seat).
Glossary: `CONTEXT.md` — Standard workbook, Standard content, and Standard ID
are ratified terms; "Bundle" and "logical id" are retired.

## Problem Statement

The foundation branch proved the contract, but it speaks a vocabulary the
second wave retired. Sync invents an Administrator-owned container workbook
per bundle, creating and garbage-collecting it by hand — a workbook in
everything but reconcile. The identity field is named `logical_id`, a name
that says what it is not. The shipping format is append-only once an app ships
content against it, so `bundle.json` must become `workbook.json` before that
happens — this is the one change with a freezing deadline. And the permission
controller enforces a model that is stated nowhere, so every new grant source
is negotiated against folklore.

Half of the identity problem solved itself while this spec waited. A sync race
(`29a1e82f`) forced the container's identity off the site global and onto the
workbook as a `logical_id`, with a patch that clears the globals. That is this
spec's identity pin, built early and for a different reason. What remains is
the reconcile: the container is still created ad hoc rather than reconciled,
and it still carries no `is_standard`.

## Solution

The shipping unit is the workbook. The manifest becomes the workbook's file,
`Insights Workbook` carries the same identity pair as the content doctypes,
and sync reconciles it as the fourth doctype — the container machinery dies
(its site global already has). `logical_id` renames to `standard_id`
everywhere. A
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
- `Insights Workbook` already carries `logical_id`, added by `29a1e82f` and
  holding `{app}/{folder}` — this spec's Standard ID, under the old name. It
  renames with the other three. What the workbook still lacks is
  `is_standard`, which this reshape adds, with a patch that sets it on every
  workbook that has a `standard_id`.
- The folder name is identity, so renaming a shipped folder deletes one
  workbook and creates another, the same event as renaming any shipped item.
  Item names stay flat per app; the folder still does not namespace them.
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
- `_container_workbook`, `_containers_of`, and `_cleanup_containers` die,
  replaced by the reconcile. The site global died already: `29a1e82f` removed
  it and `move_bundle_containers_to_logical_id.py` clears the leftovers, so
  this spec's planned migration patch is not needed. Only the `is_standard`
  backfill and the field rename remain.
- Note what `_cleanup_containers` does today that the reconcile must not
  inherit: when a shipped folder goes away it *keeps* a container the site
  put its own work into, merely clearing its identity. The membership guard
  below makes that branch unreachable, which is the whole reason deletion
  becomes ordinary. Delete the branch, do not port it.
- `standard_content()` (the gallery feed) groups by the workbook's
  `standard_id` and reads its title directly. Today it groups by
  `dashboard.workbook`, derives the app by splitting a dashboard's identity,
  and fetches each workbook's title in a per-row `get_value` — three
  symptoms of the workbook having no identity of its own to read.

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
  test name, or frontend type keeps "bundle" **for the shipping unit**.
- "Bundle" survives where it means a JavaScript asset bundle, which is
  Frappe's word and not ours. Three call sites today: `app_include_js =
  "insights_nudge.bundle.js"` in `hooks.py` with the file it names, and the
  island-size comments in `frontend/src2/query/helpers.ts` and
  `frontend/src2/helpers/navigation.ts`. The rule is by meaning, not by
  spelling: rename every bundle that is a shipping unit, keep every bundle
  that is a build artifact.
- Frontend call sites, all of them: `workbook/export_targets.ts` (types),
  `workbook/WorkbookLibrary.vue` and `workbook/WorkbookExportToAppDialog.vue`
  (props and `logical_id` reads), `workbook/WorkbookList.vue` (the
  `StandardBundle` type, the `bundles` ref, and the `get_standard_content`
  call), `workbook/WorkbookNavbarActions.vue` (a comment), and
  `dashboard/viewer.ts` (the `insights.api.bundles.duplicate_dashboard`
  path).
- **User-facing strings do change**, against what this spec first said. The
  Export to app dialog says "bundle" to the person using it, in seven
  translated strings: the `Bundle`, `Bundle Folder` and `Bundle Title` field
  labels, the `New bundle…` option, two validation messages about a bundle
  folder, and the "the bundle already matched" result line. They become
  workbook terms, and the translation source files follow. The dialog's
  `ExportBundle`, `BUNDLE_NAME_PATTERN`, `toBundleName` and `NEW_BUNDLE`
  identifiers rename with them.

### The permission controller's named model

- No behavior change. The reshape writes the model down and names the seam.
- The grant-source table from ticket 26 becomes the `permissions.py` module
  docstring. The stated rule: a new grant source must earn a row in this
  table before it earns a join in this file.
- Ticket 26's table needs two corrections before it can be the docstring,
  both found by reading the controller as it now stands. The table describes
  a grant as "a union of enumerable sources per (doctype, action)", but two
  entries do not enumerate anything — they short-circuit the whole
  controller. Write them as **bypasses**, above the sources:

  | Bypass | Applies to | Actions |
  |---|---|---|
  | Admin (`is_admin`) | every permissioned doctype | all |
  | Preview key (`has_preview_key`) | every permissioned doctype | read only |

  | Source | Applies to | Actions |
  |---|---|---|
  | Ownership | everything | all |
  | DocShare | workbook, dashboard, chart | per share flags |
  | Container inheritance | workbook→items, dashboard→chart, chart→query | follows container |
  | Team resource grant | source, table — *and* dashboard, chart (legacy) | all |
  | Audience ladder | dashboard, chart | read only |
  | Seat (`check_app_permission`) | the authoring SPA, not documents | — |

- The preview-key row is new since ticket 26. One-renderer moved the key off
  the old public read path and into the controller, so it is a grant the
  table must carry. It is a bypass and not a source because it names no
  documents: it answers "is this the site photographing its own page" and
  returns before any union is built.
- The data-query rows ticket 26's table would have carried are already gone —
  one-renderer retired them with the cache. Nothing to remove here.
- The table is exhaustive, and can say so. An earlier draft of this spec
  carved out `is_public` on the shared chart page as a grant living outside
  the controller. `3c0d5edb` retired that path whole — the `is_public` walk,
  `api/shared.py`, and the `insights_for_public_access` flag are gone, and
  the column is left with nothing reading it. Every read now goes through the
  controller, so the docstring needs no exception clause. State the closure
  as a property the table claims: a grant not in this table does not exist.
- `check_app_permission`'s docstring states its contract: the authoring
  gate — "may this person enter the builder" — never consulted for viewing.
- `can_edit` in `api/viewer.py` is already the single seat-AND-rights
  helper; it stays the only place the conjunction is assembled.

## Testing Decisions

The seams are unchanged. The suites rename with the code and grow three
cases, and the rename itself gets a gate.

- **Workbook reconcile.** In the fixture app: first sync creates the
  workbook with `standard_id`, `is_standard`, and the manifest title; a
  retitled manifest retitles it; re-sync is a no-op; removing the folder (or
  breaking `required_apps`) deletes the workbook and everything in it, in
  order; uninstall does the same.
- **Membership guard.** Creating a user query in a standard workbook throws;
  so does creating an `Insights Folder` there and moving an existing item
  in. Duplicate still lands in a user workbook untouched.
- **Identity migration.** Reduced by `29a1e82f`, which shipped the
  global-to-document migration and its test. What is left to cover: the
  `is_standard` backfill sets the flag on every workbook holding a
  `standard_id` and on no other, and a second run is a no-op.
- **Rename completeness.** Every existing suite passes under the new names,
  with fixtures shipping `workbook.json`. The suites that carry `logical_id`
  or a bundle identifier today: `test_bundles.py`, `test_bundle_export.py`,
  `test_duplicate.py`, `test_resolver.py`, `test_viewer_api.py`, and
  `workbook/test_workbook.py`. One-renderer added the shared factories in
  `tests/factories.py` plus `test_authoring_api.py`,
  `test_chart_derivation.py`, `test_chart_query_cache_retirement.py`, and
  `test_sankey_aggregation_repair.py` — they build charts and workbooks
  through the same helpers, so they move with the rename even where they
  never say "bundle".
- **The grep gate.** A test asserts no `logical_id` and no shipping-unit
  `bundle` identifier survives in `insights/` or `frontend/src2/`. Its
  allow-list is the glossary's "_Avoid_: bundle" entries, patch filenames,
  and the asset-bundle call sites named under Vocabulary. Keep the allow-list
  a literal enumeration rather than a pattern — a pattern that admits
  `*.bundle.js` would admit a renamed sync module that ships one.

## Out of Scope

- The client-side residue of the stored-list model (title mirror, index
  routes) — handed to the workbook-state-model effort by ticket 25, spun
  off separately.
- Retiring team resource grants on content doctypes — recorded as an input
  to the parked unified-permission-store effort by ticket 26.
- Every open ticket. Checked 2026-08-07: none blocks this reshape.
  [06](issues/06-vue-app-embed-ux.md) is deliberately last and blocked by 04
  and 05; [10](issues/10-site-customization-of-shipped-content.md) resolves
  behind the resolver; [11](issues/resolved/11-drill-down-interaction.md) runs in
  parallel by its own note; [28](issues/28-runtime-version-authority.md) is a
  lockfile question whose fix lives in the framework repo; and
  [29](issues/29-host-ambient-for-islands.md) is the island envelope, which
  this reshape does not touch.
- Any format addition beyond the manifest rename (shipped folders, ordering,
  layout).

## Further Notes

- **Supersedes** spec-insights-foundation pin 3 (one site-managed container
  workbook per bundle, tracked in a site global): the container is now the
  shipped workbook itself, with identity, at the same per-folder
  granularity. The other foundation pins stand.
- **Amends** ticket 04's vocabulary: references are Standard IDs. The
  resolver's accepted forms and its deny-equals-missing behavior are
  unchanged by this reshape, but there are now **four** forms, not three:
  `3c0d5edb` moved the v2 `old_name` lookup into `resolve` when it retired
  `api/shared.py`. Order is Standard ID (by the slash), then docname, slug,
  v2 name. The rename touches the first of the four and nothing else.
- **One-renderer landed first**, against both specs' stated order. It cost
  nothing: the two overlap in five files (`bundles.py`, `bundle_export.py`,
  `duplicate.py`, `permissions.py`, and the suites), and in every one
  one-renderer removed code this reshape would have had to rename.
- **Then three more commits took work off this spec**, each for its own
  reason rather than for the reshape. `29a1e82f` put the container's identity
  on the workbook to fix a sync race, which is this spec's identity pin and
  its migration patch. `3c0d5edb` retired `is_public` to remove a second
  access system, which makes the grant-source table exhaustive. `454d8716`
  removed a duplicated helper the rename would have had to rename twice.
- **The pattern is worth naming**, because it will repeat. Every one of these
  landed for a local reason and happened to be a piece of this reshape. That
  is what a spec waiting on a moving branch costs and earns: re-read the
  branch before starting, not the spec. The four claims that went stale here
  were an identity field, a migration patch, a permission exception, and the
  count of the resolver's reference forms — none of them wrong when written.
- **The freezing deadline** is the reason this reshape precedes further
  feature work: `workbook.json` and `{app}/{folder}` identity must be the
  format's first public shape. Until this lands, no app may ship content
  against the branch. One-renderer already took the per-chart data file out
  of the format, so the manifest rename is the last change the format needs
  before it freezes.
- **Folder renames after release** are delete-and-create by design. If
  demand shows, a `renamed_from` alias is the deferred mechanism, for
  folders and items alike (ticket 03's position, unchanged).
