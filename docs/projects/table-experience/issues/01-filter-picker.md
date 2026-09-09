# One filter picker

Type: task
Status: ready-for-agent

## Question

Three surfaces need to pick a column and a condition: the dashboard filter bar, the card filter button (02), and the builder's Columns popover (05). Today the bar has its own picker, and the builder's column menu has three typed bodies that the bar lacks.

## What to build

A picker in two layers.

1. **Column list.** A popover with a search box and one row per column, typed by icon. Keyboard: type to narrow, arrows to move, Enter to choose. This layer alone is the Columns popover.
2. **Condition body**, opened for a chosen column, by type:
   - Dimension: is, is not, in, contains. Values from `getDistinctColumnValues`.
   - Measure: greater than, less than, between, equals.
   - Date: range, or a relative window.

Compose the bodies from `ColumnFilterTypeText`, `ColumnFilterTypeNumber` and `ColumnFilterTypeDate` in `frontend/src2/query/components/`. Move what needs moving so nothing under `query/` is imported by `dashboard/`.

The output is a filter rule: column, operator, value. Both the dashboard bar and the card button turn it into an adhoc filter group.

## Not this ticket

The dashboard filter's icon, default value and link config stay in `DashboardFilterEditor.vue`. Only the choosing moves.
