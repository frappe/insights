# Find, client-only

Type: task
Status: ready-for-agent
Blocked by: 03

## Question

The filter row is eight empty inputs that hide a syntax (`>100`). Whether it filters in memory or re-runs the query depends on row count (`isSinglePage` in `QueryDataTable.vue`). On a card there is no server path, and a `show_filter_row` chart config decides if a reader gets the row at all.

## What to build

One find box in the table toolbar (03). It matches every column of the loaded rows, case-insensitive substring, and narrows them as you type. It never re-runs anything. It says what it covers: "in 100 loaded rows".

Remove:

- the filter row, `showFilterRow` and `filterPerColumn` in `DataTable.vue`
- `onFilterChange` and `isSinglePage` in `QueryDataTable.vue`; a server filter is a column menu act (04) or a card filter (02)
- `show_filter_row` from `chart.types.ts`, `adapter/table.ts`, its tests, fixtures and `TableChartConfigForm.vue`

Keep `matchesFilter` for the text case. The numeric operators leave with the row: a measure condition is the picker's job.

Empty result from find is the "no rows match" state in 03, with a clear action.

## Looks like

Settled in `FrameProto.vue` (branch `try/table-proto`), 2026-09-09. Find is the toolbar search described in 03, and the same input also jumps to a column. Both jobs are one control. The count in its panel is the live row-match count. Escape clears the term, so a short table never hides its cause.
