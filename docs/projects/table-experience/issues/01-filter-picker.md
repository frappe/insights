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

Compose the bodies from `ColumnFilterTypeText`, `ColumnFilterTypeNumber` and `ColumnFilterTypeDate` in `frontend/src2/query/components/`. Move what needs moving so `dashboard/` imports nothing under `query/`.

The output is a filter rule: column, operator, value. Both the dashboard bar and the card button turn it into an adhoc filter group.

## Not this ticket

The dashboard filter's icon, default value and link config stay in `DashboardFilterEditor.vue`. Only the choosing moves.

## Looks like

Settled on `frontend/src2/dev/ProtoFilter*.vue`, `ProtoDateRange.vue`, `proto_filter.ts` (branch `try/table-proto`), third pass, 2026-09-09.

- Helpdesk's three-step popover: overview → fields → value, with its slide transitions, keyboard and live apply. Trigger with a count badge; the host may replace it through the `trigger` slot.
- **No operator control.** One complete picker per type:
  - Dimension: searchable distinct-value list with a Checkbox per row, applies as `in`. Include/Exclude `TabButtons` in the header flips to `not_in`. A more menu holds Contains (toggles to a text input and back), Is set, Is not set.
  - Measure: From and To inputs. One filled is `>=` or `<=`, both is `between`.
  - Date: inline calendar with a preset sidebar. A preset emits a span from `window.ts` and highlights its resolved range; one day is `within` that day's span; two days are `between`. A preset returns to the overview, a day pick stays open so a second click can extend it.
- Overview rows are typed, not sentences: icon, column in `text-ink-gray-8` medium, `·`, value in `text-ink-gray-6`. "Acme, Bolt +2", "not Acme", "at least 500", "500 to 2,000", "Last 30 days".
- Blocked by 07 for the calendar.
