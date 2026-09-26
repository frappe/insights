# A reader never sees a false empty

Date: 2026-09-19

## Status

Accepted. Built in `desk-dashboards` tickets 13 to 17.

## Context

ERPNext's dashboards move into Insights, so every desk user becomes a reader of Insights dashboards. Desk opens a Dashboard when the user may read at least one of its charts. It hides each chart the user may not read, and runs each chart with the reader's permissions. Insights showed every card, and a table the reader could not read returned no rows. In both cases the reader sees a dashboard that is partly empty. There, "No data" looks like zero, which is false.

## Decision

A reader sees their own rows, or a message that they may not see them. An empty result never stands in for a missing permission.

- A chart is **Not Permitted** when it reads a site-DB table or permlevel column that neither the reader's desk permissions nor a team grant allows. It does not run. Its card stays in place and names the doctypes the reader needs. This is Frappe's own query rule: one unreadable table fails the whole `get_list`.
- A dashboard on which every chart is Not Permitted answers Not Found. The exception is a user who may write the dashboard, because they can fix it. A dashboard with some permitted charts opens, so its layout never changes.
- A card whose rows User Permissions narrowed says so, because a narrowed number looks like the total.

## Considered Options

- **Hide the card**, as desk does. Rejected: the layout changes from reader to reader.
- **Open a dashboard only when every chart is permitted.** Rejected: one rarely granted table would hide the whole dashboard.
- **Run the chart without the part the reader cannot read.** Rejected: it shows a different number under the same title.

## Consequences

- A chart an app ships always runs as its reader. Validation refuses a standard chart with Run as owner checked. Its owner is Administrator on every site, and ERPNext cannot know who reads it on each site. To show a company-wide number to readers who may not read its rows, a site duplicates the workbook and checks Run as owner on its copy. That disclosure is the site's decision.
- The site-wide `Insights Settings.apply_user_permissions` setting is removed. The chart's Run as owner Check is the only switch.
- A chart that left-joins an unreadable table only to get a label is Not Permitted as a whole. The author must remove the join.
