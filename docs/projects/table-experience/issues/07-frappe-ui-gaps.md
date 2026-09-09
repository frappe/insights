# Four frappe-ui gaps the picker and the pane hit

Type: task
Status: ready-for-agent

## Question

Both prototypes had to rebuild a frappe-ui piece because the component could not be used the way the design needs. Each is a small frappe-ui change, and the real build should not carry the rebuilt copy.

1. **The calendar cannot render inline.** `DateRangePicker` always owns a trigger input and its own floating panel. `CalendarPanel` is the inline piece, but it is not in the package's `exports`. Export it, or give the pickers an inline mode. Ticket 01's date picker needs this.
2. **Popover steals focus on open and toggles on every trigger click.** A typing-driven panel under an input needs the input to keep focus and the caret click not to toggle. Expose reka's `open-auto-focus` escape hatch, or a `manual` mode. Ticket 03's search panel needs this; until then it is a plain positioned box.
3. **`TextInput`'s size and variant class tables are private.** An element that is not an `input` cannot wear them: `ContentEditable.vue` carries a copy, `focus:` rewritten as `focus-within:`, so an editable title sits at the same height and takes the same focus ring as the box next to it. The copy drifts silently every time the input is restyled. Export the tables, or a `useInputClasses({ size, variant })` composable that takes the focus prefix as an argument.
4. **`ChartContainer`'s header does not center its actions on the title.** The row is `items-start`, the title line is 20px and a button is 28px, so a menu in `#actions` sits 4px low and the header grows 8px. The docs name a menu as what the slot is for. Center the actions on the title line without growing the row; `ChartBuilderActions.vue` carries `-my-1` until then.

All four go to `~/frappe/frappe-ui` on a branch, pushed to `fork`. Until they land, the app carries the prototype's copies behind a comment that names this ticket.
