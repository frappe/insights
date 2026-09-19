# Shape the framework's standard-document contract

Type: grilling
Status: open
Repo: frappe, insights

## Question

[Which mechanism ships standard content](03-which-mechanism-ships-standard-content.md) decided that frappe owns the lifecycle of an app-shipped standard document, and that Insights is its first consumer. Decide the contract's shape: how an app opts in, what frappe does from that, where the files sit, and what the first slice covers. Builder and Studio are the next consumers, so the shape must fit them without per-app layout config.

The sections below carry the unresolved part of ticket 03's grilling, with the recommendation each question had when the session ended. Read [ticket 03's answer](03-which-mechanism-ships-standard-content.md#answer) first.

## Open questions

**Q5, declaration or API.**
- **O1.** An app declares doctypes in a frappe hook, for example `standard_doctypes = [...]`. Frappe's `Document` and migrate then do import, orphan deletion, the read-only guard and export on save. Controllers call nothing.
- **O2.** Frappe exposes functions such as `guard(doc)`, `export(doc)`, `sync(app)` and `reap(app, doctype)`, and each app wires them in.

Recommended: O1, with O2's functions as the implementation. Per-controller wiring is how the pattern got copied five times. Saqib's condition: the contract must take enough code off app owners that they switch willingly, as happened with frappe's telemetry API.

Proposed route:
1. **Land:** Insights plus ERPNext.
2. **Expand outward:** Builder and Studio drop their sync code.
3. **Expand inward:** frappe moves Report, Dashboard, Print Format and Workspace onto the contract. `IMPORTABLE_DOCTYPES`, `ORPHANABLE_ENTITIES` and the per-controller guards then go.

Only step 1 is in this map. Open within Q5: the fields a declared doctype must have. `is_standard` Check, `app`, and optional `module` were proposed. Frappe's own doctypes use mixed flags (`standard = "Yes"`, `standard` Check).

**Q6, when import runs.** Builder, Studio and frappeverse all import from `after_migrate`, which runs after every app's schema has synced. They also use `after_app_install(app_name)` (`frappe/installer.py:383`) and `before_app_uninstall`. Recommended: frappe runs the same three moments once, for every declared doctype. Change detection stays on `modified`, the host convention; export on save stamps it. Saqib asked whether this matches what the apps do. It does. Not yet confirmed.

**Q7 guard, cross-app overwrite.** Import deletes and re-inserts by name (`delete_old_doc`), so two apps shipping the same name overwrite each other silently. Frappe Reports carry the same hazard. Recommended: import refuses to overwrite a document that belongs to another app, and fails the migrate loudly.

**Q11, where a file lives.** Recommended rule: a declared doctype's file lives under its **owner's** folder. The owner is its parent document when the declaration names a parent Link, and otherwise the app or module. One recursive path function, with folder names derived from the scrubbed doctype name:

```
crm/crm/builder_page/<page>/<page>.json                                          owner: app
crm/crm/studio_app/<app>/studio_page/<page>/<page>.json                          owner: Studio App
erpnext/erpnext/selling/insights_workbook/selling/insights_chart/<name>.json     owner: workbook
```

A member whose file has gone is an orphan, and a site can't add its own members under a standard parent. Frappeverse enforced that as `block_foreign_workbook_members`. Saqib asked whether an app could choose its own layout, such as `crm/crm/insights/workbook/`. The recommendation was no for the shipping app, because the walk would need per-app config. The doctype's owner declares structure (the parent Link), not folder names.

**Q12, member names.** A query or chart name is its identity on every site, so it has to be fixed before ERPNext's first commit.
- **O1.** Keep the hash.
- **O2.** Rename to `<workbook>-<title slug>` when the workbook is marked standard. `rename_doc` does not rewrite the references inside JSON, so Insights would need its own rename.
- **O3.** Use a readable file name over a hash docname. Studio carries code for the retitle drift this causes (`studio_page.py:209`).

Recommended: O1 for queries and charts. Dashboards wait on [How desk reaches a standard dashboard](04-how-desk-reaches-a-standard-dashboard.md), because desk links to one by docname.

## Conventions to carry, no decision needed

- **Code in companion files beside the JSON**, as Studio does with `.ts` and Builder with `data_script.py`. Frappe's import already supports this through `load_code_properties`.
- **Export writes everything the item needs**, as Builder does for components, fonts and variables, Studio for components, and frappeverse through `dashboard_closure`.

## Evidence

How Builder and Studio lay out files at `upstream/develop`, 2026-09-18:

```
Builder                                        Studio
<app>/builder_files/                           <app>/studio/<studio_app>/
  pages/<page>/<page>.json, data_script.py       <studio_app>.json
  components/<id>.json         shared            studio_page/<stem>/<stem>.json, .ts
  client_scripts/<name>.json   shared            studio_components/<id>.json   copied per app
  fonts/  variables/           shared
<app>/public/builder_assets/
```

- **Builder:** a page references components inside its `blocks` JSON, not through a Link. Components, scripts, fonts and variables are shared across pages, so Builder's only natural parent is the app.
- **Studio:** Studio Page is a member of Studio App through a Link (`studio_app`). Components have no link to an app.

Frappe gaps an outside app hits today (frappe `develop`, 2026-09-10):
- **Deletion:** `ORPHANABLE_ENTITIES` has no hook.
- **Fields a site changed:** `ignore_values` is hardcoded, so a re-import overwrites them.
- **Read-only guards:** written separately in each controller. Import skips `validate`, so the guard needs its own hook point.
- **Export:** `export_to_files` is called from each controller.
- **Install order:** see Q6.

## Constraints from Saqib

- Build nothing on `frappe/desk/layers.py` (`resolve_layers`), or on the Sidebar/Dock app-rooted path.
- P1 modification model: read-only plus Duplicate.
