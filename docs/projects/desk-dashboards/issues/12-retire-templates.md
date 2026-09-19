# Retire Templates

Type: task
Status: open
Repo: insights

## Question

[Which mechanism ships standard content](03-which-mechanism-ships-standard-content.md) decided that Templates retire. Standard documents plus Duplicate replace them.

**On `feat/islands`**, bound for `develop`, remove:
- the `insights_workbooks` hook (`insights/hooks.py:39`)
- `insights/api/templates.py`
- the pristine-copy restamp in `insights/migrate.py`
- `insights/workbook_templates/`
- the library UI: `WorkbookTemplates.vue`, `OpenTemplate.vue`, and its entry in `WorkbookList.vue`
- `insights/tests/test_workbook_templates.py`
- template telemetry
- the Template entry in `CONTEXT.md`

`from_template`, `imported_version` and `imported_checksum` go dead. Decide whether to drop them from the doctype now; the columns and data survive either way. A site's imported copies stay as ordinary workbooks. `skills/insights-workbook-cli/SKILL.md:208` lists workbooks by `from_template`, so update it. `insights.patches.requalify_workbook_templates` is already in `patches.txt`, so check that removing the module it imports doesn't break it.

**On `version-3-hotfix`**, as a separate PR against `upstream/version-3-hotfix`: at migrate, log a deprecation warning that names any app other than Insights that declares `insights_workbooks`. Nothing else changes on v3.

Record: what was removed, what was kept and why, and the hotfix PR link.
