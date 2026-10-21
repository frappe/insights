# A refused reader is told so

Date: 2026-10-20

## Status

Accepted. Built in `v4-release` ticket 14. Replaces the Not Found answer for refused content in `a-reader-never-sees-a-false-empty.md`.

## Context

A View answered Not Found both for a reference that names nothing and for content the reader may not read, so a probe could not tell which. In v4 every desk user reads Insights dashboards. Desk lists a board by role, and a share names a person, so the reader already knows the board exists. "Dashboard not found" then reads as a broken link. The admin who shared it cannot tell that the reader needs a permission.

## Decision

- A reference that names nothing answers Not Found (`frappe.DoesNotExistError`).
- Content the reader may not read answers No Access (`frappe.PermissionError`): "You don't have access to this dashboard" or "this chart". The reader learns that it exists, and nothing else: not its title, its workbook or its charts.
- A dashboard shared with roles names them when a signed-in reader holds none of them under "You don't have access to this dashboard": "Shared with Stock User". Who may read a board says nothing about what it shows, and the reader learns what to ask for. Added in `v4-release` ticket 66, so a Stock Manager refused the shipped Stock board knows the role it needs.
- A dashboard the reader may read, on which no chart would run for them, answers No Access with the doctypes its charts need. They may read the dashboard, so naming the doctypes reveals nothing, as on a Not Permitted card. A user who may write it still opens it.

## Considered Options

- **Keep Not Found for both.** Rejected: it hides nothing a desk sidebar or a share has not already told the reader, and it hides the fix from the admin.
- **Open the dashboard with a grid of Not Permitted cards.** Rejected: a board with nothing for the reader is not a board for them, as desk hides a dashboard with no readable chart.

## Consequences

- Whether a dashboard route or a chart docname exists can be probed, and so can the roles a dashboard is shared with, by a signed-in user. Routes are made from titles, and shipped routes are public anyway.
- A guest on a dashboard that is no longer public is sent to sign in on No Access, and sees Not Found for a link that names nothing.
