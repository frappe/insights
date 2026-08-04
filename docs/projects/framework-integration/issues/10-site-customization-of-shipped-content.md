# Site customization of shipped content

Type: grilling
Status: open

## Question

The customization model for shipped (standard) Insights content — split out of
[Content lifecycle](03-content-lifecycle.md) because the decision has
new-convention ambitions beyond Insights and confidence had not converged.

What this ticket decides:

- What a site-local customization of a shipped dashboard/chart *is* — a
  whole-document fork, an item-keyed overlay, or something else.
- The fork-resolution policy delegated by
  [Mount and renderer API](04-v1-contract-surface.md): which copy
  `{app}/{name}` resolves to at mount when a customization exists.
- The reset / staleness UX, and whether the mechanism is generic enough to
  propose as a framework convention (the standard-Workspace clobber pain is
  the motivating case).

Inputs:

- [Overlay prior-art research](../research/03-customization-overlay-prior-art.md)
  — verdict: item-keyed overlay is bounded and proven under four rules
  (vendor-owned stable keys, per-key replace only, silent skip on orphaned
  overrides, a declared customization surface); ordering/free-form layout is
  the proven danger zone (no surveyed system merges orderings).
- Candidate design from ticket 03's grilling: a site overlay that shadows the
  standard doc at the same logical id (never a sibling copy in the UI), with
  layout as one coarse key replaced wholesale and upstream items appended
  deterministically. Deep chart edits = swap in a user-owned replacement, not
  in-place edits.
- The interim floor already decided in ticket 03: standard content is
  read-only on a site; "Duplicate" is the only customization until this ticket
  resolves. Exports already assign stable item keys, so a keyed model has keys
  to hang on.

Nothing on the current frontier blocks on this: resolution lives entirely
behind Insights' resolver, invisible to the mount contract and consumers.
