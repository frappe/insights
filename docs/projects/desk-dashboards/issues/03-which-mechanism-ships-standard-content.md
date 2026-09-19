# Which mechanism ships standard content

Type: grilling
Status: resolved
Repo: insights, frappe

## Question

Two mechanisms exist in git. `develop` has Templates: `insights_workbooks` hook, `workbook.json` plus `manifest.json` per folder, imported on a library click as one editable Administrator-owned copy, updated by a manifest `version`. `demo/frappeverse` had standard content: `insights/insights/erpnext_*/` bundles with one file per query, chart and dashboard, `standard_content.py` syncing them in place as Is Standard documents, `export_to_app.py` writing back in developer mode. `feat/islands` dropped the second and kept `is_standard` on the doctypes with no writer.

The map decided a shipped ERPNext dashboard is Is Standard and appears after migrate. Decide which mechanism carries that: revive standard content, grow the template hook to seed Is Standard documents, or a third shape. The answer fixes the on-disk format ERPNext commits to, the hook name, whether Templates survive for ERPNext, and where HR (owner `hrms`) would come from.

Read both implementations with the frappeverse exports from ticket 02 open.

## Answer

Neither mechanism in git. A shipped dashboard is a **framework standard document**: the app commits files, frappe imports them on migrate, and frappe owns the whole lifecycle. The contract's exact shape is the open part, carried to [Shape the framework's standard-document contract](10-shape-the-standard-document-contract.md). ADR: `shipped-content-is-a-framework-standard-document`.

Context that decided it (Saqib, 2026-09-19): v17 has Frappe's newer apps replacing framework capabilities. Builder replaces Web Page, Studio replaces Page, and Insights replaces desk dashboards. Every one of them ships standard artifacts. So this is a pattern, and it rests on framework primitives. Where a primitive is missing, this effort builds it in frappe.

### Decided

- **Frappe owns the lifecycle.** Import on migrate, deleting orphans, the read-only guard, and export on save in developer mode all live in frappe, not in Insights. Frappe `develop` PRs are part of this map.
- **Land and expand.** Insights is the first consumer. Builder and Studio moving onto it, then frappe's own Report, Dashboard, Print Format and Workspace, are later efforts. See the map's Out of scope.
- **Identity is `name`**, fixed when the author first ships and the same on every site. There is no second identifier. A content checksum can't identify a document, because it changes with every shipped edit. A stable key beside the name (frappeverse's `standard_id`) would push reference rewriting back into the app: Insights holds references inside JSON (`items`, `operations`, filter `links`) that frappe cannot see.
- **A shipped workbook's name:** the author sets it when marking the workbook standard, defaulted to the title slug (`/insights/workbook/selling`). It never changes after the first ship. Queries, charts and dashboards keep their hash names for now (see ticket 10, member names).
- **Placement:** `app` is required, and `module` is optional. The file sits under the app's package root, or under the module folder when one is set. ERPNext uses modules. Single-module apps such as CRM, Helpdesk and LMS ship at app level.
- **Drop the `v3` suffix** from every `v3` doctype before ERPNext commits its first file. The doctype name is in each file's path and body, and it lives in another app's repo, so no patch can move it later. The v2 doctypes are already gone on `feat/islands`.
- **Templates retire.** `develop` removes the `insights_workbooks` hook, the library, the import and update path, and the four ERPNext folders. `version-3-hotfix` ships only a migrate-time deprecation warning naming any other app that declares the hook. No app in the bench does. Sites' imported copies stay as ordinary workbooks, and `from_template`, `imported_version` and `imported_checksum` go dead. `skills/insights-workbook-cli/SKILL.md:208` reads `from_template`.
- **P1 modification model:** read-only plus Duplicate. The copy stops receiving updates. P1 builds nothing on `frappe/desk/layers.py` (`resolve_layers`).
- **HR** comes from `hrms`, in its own modules, through the same contract.

### Facts gathered

- Frappe opens import to other apps (`importable_doctypes` hook, `frappe/model/sync.py:181`). Deletion (`ORPHANABLE_ENTITIES`, `sync.py:245`), fields kept on re-import (`ignore_values`) and read-only guards are hardcoded, or written separately in each controller.
- Migrate walks apps in install order, so ERPNext's files for Insights doctypes import before Insights syncs its schema. A missing table raises. An old schema stamps the file as imported, and it is then skipped. `install-app insights` imports no other app's files for its doctypes (`frappe/installer.py:358`).
- Builder (`builder_files/`) and Studio (`studio/<app>/`) each ship with their own hooks and `after_migrate` sync, read at `upstream/develop` 2026-09-18. They share only `is_standard` plus export in developer mode. Neither offers an overlay; both offer only plain duplicate. Standard-content code by app: Builder about 390 lines, Studio about 270, frappeverse Insights about 1,460.
