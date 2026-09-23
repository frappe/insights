# A reader never sees a false empty

Date: 2026-09-19

## Status

Accepted. Built in `desk-dashboards` tickets 13 to 17.

## Context

ERPNext's dashboards move into Insights, and every desk user becomes a reader. Desk admits a Dashboard when any one of its charts passes, hides the rest one by one, and runs each chart as the reader. Insights showed every card and returned empty rows from a table the reader could not read. Both leave a reader looking at a dashboard that is partly empty. "No data" there reads as zero, which is false.

## Decision

A reader sees their own rows, or is told they may not see them. Never an empty result that stands for a missing permission.

- A chart that reads a site-DB table or permlevel column that neither the reader's desk permissions nor a team grant covers is **Not Permitted**. It does not run, and its card stays in place and names the doctypes it needs. This is frappe's own query rule: one unreadable table fails the whole `get_list`.
- A dashboard reads as Not Found when every chart on it is Not Permitted, except to a caller who may write it and so can fix it. A partly permitted one opens, so the layout never shifts.
- A card whose rows User Permissions narrowed says so, since a scoped number reads as the whole one.

## Considered Options

- **Hide the card**, as desk does. Rejected: the layout shifts per reader.
- **Admit a dashboard only when every chart is permitted.** Rejected: one uncommon table would hide the whole dashboard.
- **Run the chart without the unreadable part.** Rejected: a different number under the same title.

## Consequences

- A shipped chart always runs as the reader, and validation refuses a standard chart that does not. Its owner is Administrator on every site, and ERPNext cannot vouch for any site's readers. A company-wide number for readers who cannot read its rows is a site's disclosure, made on a duplicate.
- The site-wide `Insights Settings.apply_user_permissions` retires. The chart's Check is the one switch.
- A chart that left-joins an unreadable table only for a label is Not Permitted as a whole. The author drops the join.
