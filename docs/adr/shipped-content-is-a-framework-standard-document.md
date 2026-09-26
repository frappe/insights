# Shipped content is a framework standard document

Date: 2026-09-19

## Status

Accepted.

Amended 2026-09-24: Frappe's experimental standard-document functions were removed. Insights uses Frappe's existing `importable_doctypes` import instead, which works from Frappe 16.

Amended again on 2026-09-24: Insights finds the files itself and imports each one with Frappe's `import_file_by_path`. Frappe's own import goes through apps in install order. So the files of an app installed before Insights are imported before the schema of Insights Workbook is synced, and they are not imported when Insights is installed later.

## Context

ERPNext ships its dashboards as Insights content. Two mechanisms already existed:
- **Templates:** an Admin imports an editable copy from a library.
- **Frappeverse standard content:** a sync that Insights owned. It gave each document a `standard_id` and rewrote every reference on import.

In v17, Frappe's newer apps replace framework features: Builder replaces Web Page, Studio replaces Page, and Insights replaces desk dashboards. Each app ships standard documents. Builder and Studio each wrote their own sync code, and they do not share it.

## Decision

Content that an app ships is a standard document, imported the way Frappe imports a Page or a Report. Insights finds the files after a migrate, after Insights is installed, and after another app is installed. It passes each file to Frappe's `import_file_by_path`. It will go back to the `importable_doctypes` hook when Frappe imports a hooked doctype only after every schema is synced. Insights owns the rest of the lifecycle, in `insights/standard.py`: the read-only check, the overwrite check, export on save in developer mode, and deletion of a workbook whose file is gone.

A workbook ships as one file that holds its queries, charts and dashboards, as a DocType ships with its fields. Frappe owns the path, the file write and the import of the workbook. The workbook controller owns its members: `before_export` writes them into the file, and `after_insert` creates them again on import.

Frappe imports a file only when its `modified` is newer than the database row. An edit to a member does not change the workbook's `modified`, so every export sets it first. The file is at `<module>/insights_workbook/<name>/<name>.json`. Its `module` decides which app owns it.

The document's `name` identifies it. The author sets it when they first ship the workbook, and it is the same on every site. There is no second identifier. Frappe supports a stable second key only for references in Link fields. Insights keeps its references inside JSON (dashboard `items`, query `operations`, filter `links`), so a second key would put reference rewriting back in the app. A content checksum cannot identify a document either, because it changes with every shipped edit.

## Consequences

- A shipped name can never change. A rename is a delete and a create on every site.
- A shipped workbook gets a name outside the numeric series. The author sets it, and the default is the title slug. When the author marks the workbook standard, its members are renamed once to `<workbook>-<title slug>`, and the references inside JSON are rewritten then. An import rewrites nothing.
- The file does not name a member doctype, so renaming a member doctype changes no file in another app's repo.
- Templates are removed. Two mechanisms for app-shipped content would leave the choice of foundation open.
