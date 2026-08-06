# 29 — What ambient does the host owe an island?

Type: grilling
Status: open
Blocked by: none — both instances have a working floor; the contract gap does not

## Question

[Ticket 04](04-v1-contract-surface.md) structured the mount envelope by ownership:
`host` carries framework-injected ambient, `props`/`on` carry island-specific
state. It did not say what belongs in `host`. Building the viewer surfaced two
things an island needs, cannot reach, and currently degrades on — both of them
ambient the page has and the shadow root does not.

## Evidence

**Icons do not paint.** frappe-ui's `Icon` renders `<use href="#name">` into a
sprite that `spritePlugin` appends to `document.body`. A desk page has no
`#lucide-sprite`, and a shadow root could not reach it if it did. Wiring the
author's chosen filter icon end to end (endpoint → `ViewerDashboardItem` →
`ViewerFilterBar`) therefore produced an empty 16px box — worse than the type
icon it replaced. `FilterControl.vue` now falls back to the type icon when no
sprite is present, so the SPA is unaffected and the island is no worse than
before, but the author's choice is silently discarded on desk.

Rejected as the fix: shipping the sprite with the island — 457 kB raw / 81 kB
gzip against a 152 kB budget, and it would be re-shipped per island.

**Numbers format differently on the two surfaces.** The island prints `16.45M`
and `7M` where the SPA prints `1.64Cr`. Indian digit grouping applies in the SPA
and not in the island. Pre-existing, unrelated to layout: the island never
receives the locale/format ambient the SPA reads from its own boot.

## Why one question and not two

Both are the same shape. An island is a Vue app in a shadow root on someone
else's page, and it renders correctly only if the host hands it what the page
holds ambiently. Answer them separately and `host` grows a field per symptom;
answer them together and the envelope gets a rule.

The candidates a rule has to choose between:

- **The runtime carries it.** Icons already have a precedent — CSS is solved this
  way, one shared runtime sheet adopted into every shadow root
  (`adoptedStyleSheets`, [ticket 08](08-build-ownership-and-preset.md)). A sprite
  adopted the same way costs one copy per page rather than one per island.
- **`host` carries it.** Right for anything site- or user-scoped — locale, number
  and date format, timezone, theme. These are values, not assets, and they are
  already in boot.
- **The island asks.** Cheapest to add, worst to live with: every island
  reimplements the reading, and the two surfaces drift exactly as they have here.

Settling this is also what stops the next island from discovering its own third
instance.

## Constraint

Whatever is chosen has to work for a Vue-frontend app embed too, not only desk
([ticket 06](06-vue-app-embed-ux.md)) — the host differs, the ambient need does
not.
