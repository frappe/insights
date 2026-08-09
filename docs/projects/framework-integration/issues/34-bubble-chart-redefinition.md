# 34 — Redefine the Bubble chart

Type: grilling
Status: open
Blocked by: none

## Question

Bubble renders through v2's `ScatterChart` now. The swap exposed a config that
half-serves two readings and a form that reaches neither. What is a Bubble chart
for, which options follow from that, and what happens to the ones that do not?

Bubble is seldom used, so its options and its form can be redefined rather than
preserved. Minor breaking changes are acceptable when the migration is
manageable. Every other part of this effort is bound by "existing Charts render
unchanged", so this ticket has to earn the exception.

## Evidence

Read `frontend/src2/types/chart.types.ts:152`, `charts/adapter/bubble.ts`,
`charts/components/BubbleChartConfigForm.vue` and
`insights_chart_v3/chart_query.py`.

1. **The quadrant feature is unreachable.** `show_quadrants`, `xAxis_refLine`
   and `yAxis_refLine` are stored and read, and no control sets them. Only
   `chart-gallery.workbook.json` and `insights/tests/factories.py` fill them. An
   author reaches the feature by hand-editing the config.
2. **Nothing computes a divider.** The adapter draws the numbers the author
   stored, or no rule at all. So the feature asks for two absolute numbers on
   two scales the author has not read yet.
3. **`show_data_labels` has a toggle and no reader.** v2's scatter prints no
   per-point label today. frappe-ui is fixing that separately.
4. **`xAxis` and `yAxis` are the only camelCase slots in the app.** They are
   camelCase because `SLOT_SHAPES` in `chart_query.py` is one flat dict keyed by
   slot name, and `x_axis` and `y_axis` are taken by the axis charts with
   different shapes.
5. **The Dimension that names the points is treated as decoration.**
   `_add_bubble_operation` groups by `dimension` and `quadrant_column`. With
   neither set the summarize returns one row, so the Chart draws one point. The
   form calls `dimension` "Name Column", marks it optional, and hides it under
   Options. `config_errors` does not ask for it.
6. **A Bubble's Dimensions reach the server unnamed.** `setDimensionNames` fills
   a missing `dimension_name` for `x_axis.dimension`, `split_by.dimension`,
   `date_column`, `label_column`, `rows` and `columns`. It knows neither
   `dimension` nor `quadrant_column`, which is why the adapter falls back to
   `column_name`.
7. **The form is two sections across no meaning.** "Setup" holds x, y, colour
   and size. "Options" holds the name column and one toggle inside three nested
   divs. Every other single-plot form is one "Options" section.
8. **The app already has reference lines.** Axis charts store
   `reference_lines: ReferenceLine[]` and edit them in `YAxisConfig.vue`.

## Proposal

### What a Bubble chart is for

A Bubble chart compares things against each other on two Measures. One point is
one thing. Its position says how it scores on each Measure. Its size says how
big it is. Its colour says which family it belongs to.

So the Dimension that names the points **is** the chart. Two Measures place
them, a third sizes them, and a second Dimension groups them. Every control
below follows from that sentence.

Quadrants are a second reading laid over the first: which things are ahead of
typical on both scales. That reading is worth keeping, and it is a different
question from "where is my target".

### The config

```ts
export type BubbleChartConfig = {
	label_column: Dimension
	x_column: Measure
	y_column: Measure
	size_column?: Measure
	split_by?: SplitBy
	show_data_labels?: boolean
	show_quadrants?: boolean
	reference_lines?: ReferenceLine[]
}
```

`label_column` is what Donut and Funnel already call the Dimension that names
each mark. `split_by` is what the axis charts already call the Dimension that
makes one series per value, and it is the same idea here — v2 takes both as
`series`. `x_column` and `y_column` follow the `<role>_column` convention and
sit beside `size_column`.

They are not `x_axis` and `y_axis`. `SLOT_SHAPES` is one dict, and a second
shape under a name already in it is the defect ADR-0001 was written about.

`label_column` joins `config_errors` as required. A Bubble that names no
Dimension draws one point, which is not a reading anybody asked for.

`split_by` stores no `max_split_values` for a Bubble. Nothing on the server caps
the group count of a summarize, and a control that changes nothing is worse than
no control. The slot can gain the cap later without a rename.

**The camelCase is worth fixing.** Not on tidiness. The migration below needs a
patch for the quadrant decision whatever else it does, so the rename rides free.
And the two Dimension slots then fall under `setDimensionNames` branches that
already exist, which removes the adapter's `column_name` fallback and the
unnamed columns behind it.

### Quadrants, and reference lines

Three keys carry two readings. Split them.

**A line at a number the author knows** — a break-even, a budget, last year —
is a reference line. Bubble takes the same `reference_lines` list the axis
charts store, with `axis: 'x' | 'y'`, which is what v2's `ReferenceLine` reads
on a scatter. `xAxis_refLine` and `yAxis_refLine` stop existing.

**A line that splits the points at typical** is the quadrant. It is derived from
the plotted data, so it needs no number. `show_quadrants` becomes one toggle,
and Insights computes the two dividers and passes them as reference lines. The
arithmetic is Insights' work because v2 draws data and does not compute a
caller's numbers.

**The divider is the median** of the plotted values, one per axis, and it is not
weighted by the size Measure. A quadrant chart is read as "which things are
ahead of typical on both". Revenue, margin and order counts are right-skewed, so
a mean and a range midpoint both sit above most of the points and drop nearly
everything into one quadrant. A median splits the points about evenly whatever
the shape of the data. It also always sits inside the plotted range, so v2 never
clips it — which a typed target can be.

The two rules draw dashed and carry no label. A label there competes with the
point labels for the same pixels.

### The form

One `CollapsibleSection` titled "Options", as Donut, Funnel and Sankey have.
Controls in the order the reading builds:

1. `DimensionPicker` — "Label" → `label_column`
2. `MeasurePicker` — "X" → `x_column`
3. `MeasurePicker` — "Y" → `y_column`
4. `MeasurePicker` — "Size" → `size_column`
5. `DimensionPicker` — "Split By" → `split_by.dimension`
6. `Toggle` — "Show Data Labels"
7. `Toggle` — "Show Quadrants"
8. `ReferenceLineList` — "Reference Lines"

The reader meets what a point is, then where it sits, then how it is sized and
grouped, then what is printed over it. Required slots first, optional after.

Nothing bespoke. The one new component is `ReferenceLineList.vue`, lifted out of
`YAxisConfig.vue` unchanged, so the two charts edit a reference line the same
way. `SplitByConfig.vue` is not reused, because its section carries the cap
Bubble does not store.

This depends on frappe-ui printing a per-point label on the scatter. The text is
the `label` key when the caller named one, not the y value. That asks v2 for no
new prop.

### The migration

One patch, `insights.patches.redefine_bubble_config`, on the model of
`repair_sankey_value_aggregation`. It reads every `Insights Chart v3` row with
`chart_type = "Bubble"` and writes with `update_modified=False`, so the
standard-content guard has no save to block.

It renames `xAxis` → `x_column`, `yAxis` → `y_column`, `dimension` →
`label_column`, and `quadrant_column` → `split_by.dimension`. `size_column` and
`show_data_labels` do not move.

For the quadrant keys it has one rule: **no stored Chart changes its picture.**
Each of `xAxis_refLine` and `yAxis_refLine` that holds a number becomes
`{axis, value, dashed: true}` in `reference_lines`. `show_quadrants` is then
cleared on every Chart. A Chart that set no number drew no rule, so it loses
nothing. A Chart that set numbers keeps the same two dashed rules in the same
places, and the author can now see and edit them. `show_quadrants` is false
everywhere afterwards, and only a person turns the new meaning on.

That rule is why the count of Bubble Charts in the wild does not need to be
known. It is also why nothing needs to be shown to an author about an option
that no longer exists — every key has a destination.

The one case the patch cannot repair is a Bubble with no Dimension. It draws one
point today, and there is no column to guess. The author sees "Label is
required" in the card's error state and fills one picker. That is the accepted
break.

`normalizeChartConfig` maps the old names on read as well, because a config also
arrives from a template JSON the patch never saw. `chart-gallery.workbook.json`,
`insights/tests/factories.py` and `charts/adapter/fixtures.ts` are rewritten in
the same commit.

**ADR-0001 does not change this.** Its split folds the selection slots into
`dimensions[]` and `measures[]` positionally, and the order it needs — label
then split, x then y then size — is the order `_add_bubble_operation` already
lists, so nothing here is decided twice. The display keys survive the split into
`display.Bubble` unchanged, so they are worth naming right now whatever follows.
Renaming now hands that normalizer one coherent slot list to read, instead of a
camelCase pair and a slot named for an axis this chart does not have.

## Acceptance criteria

- [ ] A ratified reading, with every option traced back to it
- [ ] The slot names ratified or rejected, and the `SLOT_SHAPES` collision
      answered either way
- [ ] Quadrants kept with a stated divider rule, or removed outright
- [ ] The patch rule ratified as "no stored Chart changes its picture", or
      replaced
- [ ] frappe-ui confirms the scatter prints the `label` key per point
