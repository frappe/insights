# Desk dashboards — decision map

Phase 1 of framework integration. ERPNext's standard dashboards become Insights content, reached from the workspace sidebar, read on frappe.io.

Tickets live in `issues/`, one question each. A ticket carries a `Type:`, a `Status:`, and any `Blocked by:` tickets. Frontier: open, unblocked, unclaimed, lowest number first. One ticket per sitting.

Charted 2026-09-16 on `feat/islands`.

## Destination

ERPNext `develop` ships its standard dashboards for Accounts, Payments, Selling, Buying, Stock and Asset as Insights standard content. Each opens in desk from the workspace sidebar item that reaches it today. They run on frappe.io, and the Frappe teams that read them have reviewed them once.

## Notes

- Branch: `feat/islands`, worktree `insights-islands`. Rebased onto `upstream/develop` first, then all work continues on this branch. Close-out: `/iris-review` loop until clean, prose check, history cleanup, merge.
- Three repos: `frappe` (island host, and owner of the standard-document contract; its PRs go to `develop`), `insights`, `erpnext` (ships the content). A ticket names its repo.
- frappe.io runs frappe, erpnext and insights on `develop`.
- The frappeverse dashboards are the base for review, not `develop`'s four templates. They live only in the `demo.erpnext.localhost` database: workbooks 47 Business Overview, 49 Purchase & Payables, 54 Receivables, 55 Stock, 56 HR, 57 Selling. The `demo/frappeverse` branch holds the older four as `insights/insights/erpnext_*` bundles in the `standard_content.py` shape, which `feat/islands` dropped.
- Glossary (`CONTEXT.md`): Template is an editable copy from the `insights_workbooks` hook. Is Standard is read-only, synced in place, `can_copy` is its affordance. A shipped ERPNext dashboard is Is Standard.
- This map carries execution as tasks where the destination needs it (deploy, measure). The decisions come first.
- Skills: `/grilling` and `/domain-modeling` on every grilling ticket. `/insights-workbook-cli` for reading or moving workbooks between sites.
- Standing rules: ask Saqib rather than rely on memory; one decision ticket per sitting.

## Decisions so far

Decided while charting, before tickets existed.

- **ERPNext owns the content.** One shipped dashboard per ERPNext dashboard the sidebar links today, from ERPNext's own tree. Insights ships none for ERPNext.
- **A shipped dashboard is there after migrate.** No library click. The sidebar link opens a dashboard, not a gallery.
- **A shipped dashboard is Is Standard.** Read-only outside developer mode, app files are the truth, sync updates in place. A site customizes by duplicating. This reverses the 2026-08-11 template-update reasoning.
- **Modules in scope**: Accounts, Payments, Selling, Buying, Stock, Asset. CRM (deprecated), Project (not comprehensive) and Manufacturing (no reviewer at Frappe) are out.
- **Review is one sitting.** All six dashboards, all feedback at once, on frappe.io.
- **Live queries only.** No snapshots, no data store. The 60 s timeout is the backstop; load is measured before review.

Resolved tickets.

- [Rebase feat/islands onto develop](issues/01-rebase-islands-onto-develop.md) — one three-way merge, then five commits. Readers go through `insights.api.view` only, with develop's card filters and filter picker. develop's templates survive.
- [Which mechanism ships standard content](issues/03-which-mechanism-ships-standard-content.md) — neither: a framework standard document, lifecycle owned by frappe, identity is `name`. Placement is app or module, the `v3` suffix drops before shipping, Templates retire. ADR `shipped-content-is-a-framework-standard-document`.

## Not yet specified

- Business Overview has no ERPNext dashboard to attach to. Whether it ships, and from which workspace, waits on the desk-entry decision.
- HR is a seventh dashboard, shipped by `hrms` through the same contract. Whether it rides this effort is still open.
- Executing ticket 03: the `v3` rename, Template retirement on `develop`, and the deprecation warning on `version-3-hotfix`. Each becomes a task once ticket 10 sets the order against the frappe PRs.
- What a site sees when ERPNext ships a changed dashboard and the site has duplicated it. Falls out of Is Standard, but the reader-facing behaviour has not been stated.
- Default filters and date ranges per dashboard, and whether a site can set them without duplicating (the preference overlay idea).

## Out of scope

Phase 2, authoring: a user builds a dashboard or chart and places it in desk. Includes the customize UX around Duplicate, workspace chart and number-card blocks, and the research on whether the framework should own a frappe-ui chart island. Gets its own map when this one closes.

Phase 3, migration and locking: converting custom Dashboard Chart, Number Card and Dashboard records, v16 paths kept working, doctypes locked in v17, Number Card dropped. Bound to the v17 release, its own map.

Expanding the standard-document contract: Builder and Studio moving onto it, then frappe's own Report, Dashboard, Print Format and Workspace. This map lands the contract with Insights as its first consumer.
