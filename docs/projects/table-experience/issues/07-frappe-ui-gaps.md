# Four frappe-ui gaps the picker and the pane hit

Type: task
Status: in-review

## Question

Both prototypes had to rebuild a frappe-ui piece because the component could not be used the way the design needs. Each is a small frappe-ui change, and the real build should not carry the rebuilt copy.

1. **The calendar cannot render inline.** `DateRangePicker` always owns a trigger input and its own floating panel. `CalendarPanel` is the inline piece, but it is not in the package's `exports`. Export it, or give the pickers an inline mode. The filter picker's date stage needs this.
2. **Popover steals focus on open and toggles on every trigger click.** A typing-driven panel under an input needs the input to keep focus and the caret click not to toggle. Expose reka's `open-auto-focus` escape hatch, or a `manual` mode. Ticket 03's search panel needs this; until then it is a plain positioned box.
3. **`TextInput`'s size and variant class tables are private.** An element that is not an `input` cannot use them: `ContentEditable.vue` carries a copy, `focus:` rewritten as `focus-within:`, so an editable title sits at the same height and takes the same focus ring as the box next to it. The copy drifts silently every time the input is restyled. Export the tables, or a `useInputClasses({ size, variant })` composable that takes the focus prefix as an argument.
4. **`ChartContainer`'s header does not center its actions on the title.** The row is `items-start`, the title line is 20px and a button is 28px, so a menu in `#actions` sits 4px low and the header grows 8px. The docs name a menu as what the slot is for. Center the actions on the title line without growing the row; `ChartBuilderActions.vue` carries `-my-1` until then.

All four go to `~/frappe/frappe-ui` on a branch, pushed to `fork`. Until they land, the app carries the prototype's copies behind a comment that names this ticket.

## Done, 2026-09-11

Four commits on `picker-gaps` in `~/frappe/frappe-ui`, off v1.0.0-beta.63, not yet pushed.

1. `CalendarPanel` is exported, with a `v-model` that is a date or a `[from, to]` pair; the bound shape picks the mode. The pickers still pass `weeks` and own their selection, so the panel has one branch: `weeks` present means the parent owns it.
2. `Popover` gains `autoFocus` (default true) and `trigger: 'click' | 'manual'`. Manual renders reka's anchor, so it carries no `aria-expanded`.
3. `useInputClasses` lives in `frappe-ui/experimental`, next to `useInputLabeling`, not the root. `TextInput` consumes it.
4. `ChartContainer`'s actions wrapper is `h-[1lh] items-center`. The title line box measures 21px, so `min-h-7` would grow it and `-my-1` only fits a 28px action.

The prototype reads the branch through the link; the app's pin stays beta.62 until a release carries these.

## Follow-ups from the first consumer

The palette took `CalendarPanel` and `autoFocus` the same day. Three things the panel does not yet say:

- It moves focus to the clicked day. A panel inside another input needs a way to never take focus; the palette puts `@mousedown.prevent` on the panel root for now.
- It has no "the range is settled" signal. `change` fires `[from, '']` on the first click and the pair on the second, so the consumer re-derives the phase from the payload. A `complete` event would say it.
- `change` is typed as the union whatever shape is bound, so a range consumer narrows in every handler.
