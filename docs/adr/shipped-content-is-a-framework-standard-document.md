# Shipped content is a framework standard document

Date: 2026-09-19

## Status

Accepted. The contract's shape is still being decided in `desk-dashboards` ticket 10.

## Context

ERPNext ships its dashboards as Insights content. Two mechanisms already existed:
- **Templates:** an editable copy an Admin imports from a library.
- **Frappeverse standard content:** an Insights-owned sync that gave each document a `standard_id` and rewrote every reference on import.

In v17, Frappe's newer apps replace framework capabilities: Builder replaces Web Page, Studio replaces Page, and Insights replaces desk dashboards. Each ships standard artifacts. Builder and Studio already wrote their own sync code, and neither shares it.

## Decision

Content an app ships is a standard document whose lifecycle frappe owns: import on migrate, orphan deletion, the read-only guard, and export on save in developer mode. Insights is the contract's first consumer, not its owner.

Identity is the document's `name`, fixed when the author first ships it and the same on every site. There is no second identifier. Frappe can handle a stable key only for references in Link fields. Insights keeps its references inside JSON (dashboard `items`, query `operations`, filter `links`), so a key beside the name puts reference rewriting back in the app. A content checksum can't serve as identity either, because it changes with every shipped edit.

## Consequences

- A shipped name can never change. A rename is a delete and create on every site, so the `v3` doctype suffix drops before anything ships.
- A shipped workbook takes a name outside the numeric series, set by the author and defaulted to the title slug.
- Templates retire. Two mechanisms for app-shipped content would leave the foundation undecided.
