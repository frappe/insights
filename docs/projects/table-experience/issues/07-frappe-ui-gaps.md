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

## Done, 2026-09-12

Six commits on `picker-gaps` in `~/frappe/frappe-ui`, off v1.0.0-beta.63, not yet pushed.

1. `DateCalendar` and `DateRangeCalendar` ship from `frappe-ui/experimental`, each owning its selection. The range calendar holds the `[from, to]` pair, the hover preview and the first-click rule. `CalendarPanel` stays internal, which reverses the first answer: exporting the panel left every consumer rebuilding the selection around it.
2. `Popover` gains `autoFocus`, `trigger: 'click' | 'manual'`, `reference` and a `contentEl` on the template ref. Manual renders reka's anchor, so it carries no `aria-expanded`.
3. `useInputClasses` lives in `frappe-ui/experimental`, next to `useInputLabeling`, not the root. `TextInput` consumes it.
4. `ChartContainer`'s actions wrapper is `h-[1lh] items-center`. The title line box measures 21px, so `min-h-7` would grow it and `-my-1` only fits a 28px action.

## What the app took, 2026-09-12

Three of the four are in. `FilterPickerCalendar` renders the two calendars and keeps only the text mapping, since the calendars seed their own view from the value. `ResultFind` is a real `Popover` on `trigger="manual"` and `:auto-focus="false"`, so the panel is portalled and carries no `z-[100]`. `ChartBuilderActions` dropped its `-my-1`.

`ContentEditable` keeps its copy. `useInputClasses` does not fit it: the composable's `ghost` is `border-0` with no focus surface, where this box draws a transparent border that recolors on focus, and its size table carries a font-size that a caller's own `text-lg-semibold` would have to outrank. Taking it would change the look at all four call sites. The gap is narrower than it was, not closed — it wants a `ghost` that rings on focus, and type left to the caller.

**The app does not build on the beta.62 pin**, and did not before this either: the calendars, `autoFocus` and the composable are all unreleased. `wt link frappe-ui` is what builds it until `picker-gaps` is pushed and a release carries it.

## Follow-ups from the first consumer

The palette read the branch through the link. Two things the calendars do not yet say:

- They move focus to the clicked day. A calendar inside another input needs a way to never take focus; the picker puts `@mousedown.prevent` on the wrapper for now.
- There is no "the range is settled" signal. `select` fires `[from, '']` on the first click and the pair on the second, so the consumer re-derives the phase from the payload. A `complete` event would say it.
