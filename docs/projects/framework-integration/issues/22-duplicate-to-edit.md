# 22 — Duplicate to edit

Type: task
Status: ready-for-agent
Blocked by: 17, 20
Spec: [spec-insights-foundation.md](../spec-insights-foundation.md), "Customization floor"

## What to build

The v1 customization floor. Standard content is read-only on a site —
"Duplicate" is the only customization: a server-side copy of the content
closure (dashboard, charts, queries) into a user-owned workbook, the same
shape template import produces today. The duplicate is an ordinary user
document with its own identity — it is never returned for the shipped
logical id. Duplicate requires authoring access.

The island's overflow menu gains "Duplicate to edit" on read-only shipped
content, driven by the capability flags, opening the duplicate in Insights
in a new tab.

The duplicate-beside-original UX is acknowledged debt. The real
customization model is ticket 10's open question and lands behind the
resolver later.

## Acceptance criteria

- [ ] Duplicating a shipped dashboard creates a user-owned workbook with
      copies of the dashboard, its charts, and their queries
- [ ] The copy is editable, the standard stays read-only, and the shipped
      logical id still resolves to the standard
- [ ] Duplicate requires authoring access — a pure viewer cannot invoke it
- [ ] "Duplicate to edit" appears in the island overflow only for shipped
      content and permitted users, and opens the copy in Insights
