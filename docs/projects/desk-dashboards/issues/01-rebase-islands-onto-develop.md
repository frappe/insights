# Rebase feat/islands onto develop

Type: task
Status: resolved
Repo: insights

## Question

`feat/islands` is 102 ahead and 57 behind `upstream/develop` (charts-extract merged as #1383, beta.65 pin, cache and data-store fixes, 4.0.0-dev bump). Rebase, resolve, and confirm the branch builds and its suite passes on `test2.insights.localhost` before any content work lands on it.

Record here: the conflicts met and how each was resolved, and whether the four `workbook_templates/` kept the `feat/islands` version or `develop`'s (see the map's fog).

## Answer

Rebased on 2026-09-19 onto `upstream/develop` at `b996950f5`. Old tip is tagged `islands-pre-rebase-2026-09-19`, the resolved tree `islands-merge-resolved`.

The first 66 commits were pre-squash charts-extract, which #1383 merged rewritten, so only the islands commits (`e197a2c0f..d6101eeec`) were carried. Replaying them one by one meant resolving the same regions against develop about six times each, so the islands end state went on in one three-way merge (base `e197a2c0f`). History was then rebuilt as five commits, each dated from the latest original it absorbs: permissions, view, island, fixes, docs. Each commit imports every module and passes vitest.

Conflicts and how each was resolved:

- **Public fallback.** develop hardened `run_doc_method`'s public path (`PUBLIC_METHOD_ARGS`, share links routed through `stored_dashboard_items`). The islands removed that path, so readers go through `insights.api.view` only, and develop's routing is the view's `routed_filters`.
- **Reader features develop added.** `api/view.py` now takes `card_filters` and answers `comparison_rows`. It gained `get_filter_range`, `get_card_values` and `get_card_range`, and a `surface` for `dashboard_viewed` (new value `desk`). Guest views count again, because `site_profile` reads them.
- **`permission_user_for`.** develop deleted it as a no-op. It is restored, and wraps `get_data` and both drill entry points, so an owner's-rows chart drills as its owner.
- **Share telemetry.** `share_granted` for org and public moved from the retired `update_access` into `validate_visibility`, and fires when a document widens to Everyone or Public.
- **`get_data`.** It takes routed `adhoc_filters` (islands) plus `card_filters`, and keeps develop's SQL strip, period order and comparison rows.
- **Frontend.** `chart_view.ts` is develop's `chart_read.ts` (per-surface cache, stale marks) in the islands' words. `DashboardView` is widened with card filters and ranges. The builder and every reader draw the same `DashboardFilter` (develop's filter picker) and one chart cell (`chart_cell.ts`): `DashboardChart` in the builder, `DashboardChartView` for readers, kept apart so an island never bundles the authoring drill. `FilterControl` is gone. Cell rules, including develop's filter-row rule, live in `view.ts`.
- **Build.** The `patch-package` postinstall is back for the framework's reka-ui patch. frappe-ui is on beta.65, and `yarn.lock` is regenerated.
- **Tests.** develop's tests of the retired mechanisms are dropped. `test_drill_api` stays develop's layer suite, plus the view access tests. `docs/features.md` gains a `desk` area and restates the `shared` rows. Two slugs were renamed: `shared.rows-are-the-owners` and `permissions.authoring-needs-role`.

Workbook templates: develop's four `workbook_templates/` survive unchanged. The `feat/islands` differences were charts-extract-era changes that develop superseded.

Verified: 920 backend tests green on `test2.insights.localhost` after a migrate from this branch, 489 vitest, the SPA and both islands build (dashboard 1452 kB, chart 1398 kB JS), the boundary lint, pre-commit, and `features.py check`. The e2e suite was not run. `yarn build:islands` writes into `develop-bench/apps/insights/.../dist/island` and the bench's `assets.json`.
