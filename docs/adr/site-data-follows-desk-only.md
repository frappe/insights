# Site data follows desk only

Date: 2026-10-20

## Status

Accepted. Built in `insights_team.check_table_permission`, `insights_table_v3.apply_user_permissions` and `permissions._build_table_permission_query`.

## Context

Desk dashboards move into Insights, so a desk user reads Insights charts inside desk. Insights before v3.50 ANDed a team grant with desk permissions on the site database: a grant let a reader in, and desk then filtered the rows. The develop branch made it an OR, so a team grant gave rows and permlevel columns that desk denies, and a Table Restriction widened desk instead of narrowing it. On a site upgraded from Insights before v3.50, a team member would see on a desk board the rows their User Permissions hide in desk.

## Decision

On the site database, desk permissions are the only authority. A reader reads a table when desk lets them read its doctype, and gets the rows and columns desk gives them. A team grant neither widens nor narrows this, and a Table Restriction does not apply. An admin is not exempt. On every other source, a team grant is still the only access.

## Considered Options

- **OR, as on develop.** Rejected: a grant shows rows that desk denies, and a later release cannot take back data already read.
- **AND, as in Insights before v3.50.** Rejected: two authorities over one document set, and a desk user in no team could not read a desk board.

## Consequences

- A user who reached a site table only through a team grant gets Not Permitted. Insights before v3.50 gave them an empty chart, or every row where Apply User Permissions was off. The fix is a desk role that reads the doctype.
- A Table Restriction on a site table stops applying. A User Permission is the desk way to keep the narrowing.
- The upgrade lists both for the admins as `P17` upgrade items (`patches/report_site_data_follows_desk.py`), one per user and one per team, each with its fix.
- Trusted code is the exception (`code-in-a-query-follows-the-server-script-model.md`): a script, an expression that calls `.sql` or a stored procedure call reads what its code reads, and every reader of its chart sees those rows. Only an Insights Admin can add or change it.
