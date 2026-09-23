# Shipped content is a framework standard document

Date: 2026-09-19

## Status

Accepted. Amended 2026-09-24: frappe's experimental standard-document functions were dropped, and Insights uses frappe's existing `importable_doctypes` import instead, which works from frappe 16. Amended again the same day: Insights walks the files itself and imports each through frappe's `import_file_by_path`, because frappe's walk runs in install order: an app installed before Insights has its files imported before this doctype's schema is synced, and not at all when Insights is installed.

## Context

ERPNext ships its dashboards as Insights content. Two mechanisms already existed:
- **Templates:** an editable copy an Admin imports from a library.
- **Frappeverse standard content:** an Insights-owned sync that gave each document a `standard_id` and rewrote every reference on import.

In v17, Frappe's newer apps replace framework capabilities: Builder replaces Web Page, Studio replaces Page, and Insights replaces desk dashboards. Each ships standard artifacts. Builder and Studio already wrote their own sync code, and neither shares it.

## Decision

Content an app ships is a standard document, imported the way frappe imports a Page or a Report. Insights finds the files after a migrate, an install of Insights, or an install of another app, and hands each to frappe's `import_file_by_path`. It moves back to the `importable_doctypes` hook once frappe imports a hooked doctype after every schema is synced. Insights owns the rest of the lifecycle in `insights/standard.py`: the read-only guard, the overwrite guard, export on save in developer mode, and the deletion of a workbook whose file is gone.

A workbook ships as one file that carries its queries, charts and dashboards, the way a DocType ships with its fields. Frappe owns the path, the write and the import of the workbook. The controller owns its members: `before_export` writes them into the file, and `after_insert` restores them during an import.

Frappe imports a file only when its `modified` is newer than the row. A member's edit does not move the workbook's `modified`, so every export stamps it first. The file sits at `<module>/insights_workbook/<name>/<name>.json`, and `module` is the owner.

Identity is the document's `name`, fixed when the author first ships it and the same on every site. There is no second identifier. Frappe can handle a stable key only for references in Link fields. Insights keeps its references inside JSON (dashboard `items`, query `operations`, filter `links`), so a key beside the name puts reference rewriting back in the app. A content checksum can't serve as identity either, because it changes with every shipped edit.

## Consequences

- A shipped name can never change. A rename is a delete and create on every site.
- A shipped workbook takes a name outside the numeric series, set by the author and defaulted to the title slug. Its members are renamed to `<workbook>-<title slug>` once, when the author marks it standard, and the references inside JSON are rewritten then. Nothing is rewritten on import.
- The file names no member doctype, so renaming one touches no file in another app's repo.
- Templates retire. Two mechanisms for app-shipped content would leave the foundation undecided.
