# Drop the v3 suffix

Type: task
Status: open
Repo: insights

## Question

[Which mechanism ships standard content](03-which-mechanism-ships-standard-content.md) decided that every `v3` doctype loses its suffix before ERPNext commits its first file. The doctype name sits in each shipped file's path and body, and those files live in another app's repo, so no patch can rename it afterwards.

Seven doctypes on `feat/islands` carry the suffix: Chart, Dashboard, Dashboard Chart, Data Source, Query, Table Link, Table. None of their v2 namesakes remain in code. The suffix appears in 137 files and 3,416 lines across `insights/`, `frontend/src2/` and `skills/` (measured 2026-09-19).

Rename them with a patch that runs on existing sites, and update every reference: Python, the frontend, fixtures, `workbook_templates/` if it still exists, `skills/` and `CONTEXT.md`.

Check before you start:
- Sites that still hold v2 tables (`tabInsights Query` and the others). The rename's target table has to be free. v2 data may still be waiting for the v2 migrator.
- Whether `old_name` and the resolver's v2-name lookup keep working after the rename.
- Other sessions are editing `feat/islands` at the same time. Land the rename in one sitting and tell them.

Record: the patch and its order in `patches.txt`, how v2 tables were handled, and any reference the rename could not rewrite.
