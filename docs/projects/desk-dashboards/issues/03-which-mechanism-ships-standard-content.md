# Which mechanism ships standard content

Type: grilling
Status: open
Repo: insights

## Question

Two mechanisms exist in git. `develop` has Templates: `insights_workbooks` hook, `workbook.json` plus `manifest.json` per folder, imported on a library click as one editable Administrator-owned copy, updated by a manifest `version`. `demo/frappeverse` had standard content: `insights/insights/erpnext_*/` bundles with one file per query, chart and dashboard, `standard_content.py` syncing them in place as Is Standard documents, `export_to_app.py` writing back in developer mode. `feat/islands` dropped the second and kept `is_standard` on the doctypes with no writer.

The map decided a shipped ERPNext dashboard is Is Standard and appears after migrate. Decide which mechanism carries that: revive standard content, grow the template hook to seed Is Standard documents, or a third shape. The answer fixes the on-disk format ERPNext commits to, the hook name, whether Templates survive for ERPNext, and where HR (owner `hrms`) would come from.

Read both implementations with the frappeverse exports from ticket 02 open.
