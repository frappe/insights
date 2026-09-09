# One frame around every grid

Type: task
Status: ready-for-agent

## Question

The builder, the native editor and the script editor each assemble the frame around the grid by hand. The cache line is written three times. Alerts sit in the footer, export sits in the footer, the execution error is a banner that pushes the grid down.

## What to build

A result pane that the builder, native, script, drill and data source views all mount. Three bands:

1. **Table toolbar.** Columns (05), find (06), filter chips, export. Execute and the query's More menu stay in the editor's own toolbar above it.
2. **Grid.**
3. **Footer.** One status line: "100 of 4,210 rows · fetched in 1.2s · 2 min ago", or "from cache". "Running" while executing. In the native and script editors, which do not auto-execute, "edited since last run" with a Run action. Pagination on the right, as now.

Moves:

- `QueryExecutionStatus.vue` and the copy in `ScriptQueryEditor.vue` go. The footer says it.
- `QueryAlerts` leaves the footer for the editor's More menu.
- Export leaves the footer for the toolbar.

States: the grid body has one slot with three states. Execution error, no data, and no rows match your find, the last with a clear action. No banner above the grid.

Loading is one state: body dims, footer says running. The veil-versus-dim split goes.
