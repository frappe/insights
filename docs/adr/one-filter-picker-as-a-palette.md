# One filter picker, as a palette

Date: 2026-09-11

## Status

Accepted. Built in `frontend/src2/components/filter_picker/`, wired to the dashboard filter, the table chart card and the drill rows. The builder's column filter is still to be wired; until then its legacy header filter and the picker overwrite each other's adhoc dict on the drill grid.

## Context

Four hosts let a reader narrow rows by column, operator and value: the dashboard filter, the table chart card, the drill rows, and the builder's column-header filter. Each had its own control, and the dashboard's lacked the builder's typed bodies. A table card had no filter at all. Six prototypes were tried in one day; the verdicts are below.

## Decision

One component serves every host. A host with the column already chosen mounts it with `column` set and it opens on the operator stage; the others open on a column list.

The picker is a palette: one search input, and under it a list per stage, column then operator then value. Typing narrows the list, Enter picks, Backspace on an empty input steps back, Cmd+Enter commits. Applied filters show on an overview stage inside, never as chips in the host. A multi-value pick commits when the popover closes; every other value commits on Enter. No Apply button.

Every stage is a list, the value stage included. Operator rows read the word with the sign as a note; the kind's default is first. Text splits `is` (a multi-select over distinct values, `in`) from `equals` (typed). Typing is the value for numbers and dates: no inline inputs, no slider. A calendar draws inline under the input for `between` and the comparisons, and writes into the input; `within` lists presets, then Relative as further list stages (Last / Next / This, a count, units). Legacy date shapes the old controls wrote still read.

A card filter is a dashboard filter the reader owns: a filter item linked to the one chart, unsaved, folded into the surface's filter context, keyed by the chart name so the server lands it after the chart's summarize and measures work. The drill drops the chart-keyed group, since a drilled row already passed it. Card filters live in the dashboard store per chart and reset on reload.

The list stands on reka's `ComboboxRoot`, since frappe-ui's `Combobox` has no seam for a node between rows; `reka-ui` is declared. The calendar is frappe-ui's `CalendarPanel`, exported for this.

## Rejected

- Include/exclude tabs instead of an operator; from/to inputs inferring the operator.
- A sentence typed into one input; flat column · operator · value rows; chips in the toolbar; a Done row; dates without an operator stage.
- A filter button on every chart. Clicking a chart element to cross-filter is a separate effort.
- Keying card filters by the source query: lands before the summarize, so no measures and no chart labels.

## Consequences

`dashboard/` imports nothing under `query/`. `Filter.vue` is gone. A public link cannot fetch distinct values for a card filter yet; the values endpoint serves only saved filters.
