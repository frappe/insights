# Mount and renderer API

Type: grilling
Status: open

## Question

The concrete API a consumer app programs against, now that the mechanism is
settled (island via `mountVueIsland`) and the ownership split is drawn.

**The mount call.** What framework's page invokes to put an Insights dashboard
or chart into an element:

- Host context in: which document, filters, theme, locale, read-only vs
  interactive.
- Events out: drill-down requests, filter changes, navigation ("open in
  Insights"), errors.
- Lifecycle: teardown, re-mount, loading and error states.
- `mountVueIsland` gaps ticket 02 found: no app-config hook, `<link>` per
  shadow root.

**Identity.** How an app references a chart or dashboard so the reference
survives export, import, and rename — and how the chart→query reference stays
stable and addressable (the datasets-later constraint).

**The renderer toggle.** Framework's page decides Insights vs legacy from three
conditions: is Insights installed, is the feature flag on, is this document an
Insights dashboard or a legacy `Dashboard`. Settle where that lives, how apps
opt in, and how it retires.

Resolves into the shape a spec can be written from.
