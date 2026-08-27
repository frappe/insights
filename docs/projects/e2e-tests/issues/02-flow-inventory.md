# 02 — The flow inventory and its ranking

Type: grilling
Status: resolved

## Question

What is the list of user flows the suite must cover, and which 80% are in?

Draft the inventory from the code before grilling: 14 routes in
`frontend/src2/router.ts`, the area folders under `frontend/src2/`, and the
churn concentration (`query` 112 files changed in 3 months, `workbook` 83,
`charts` 76, `dashboard` 60).

Then rank with the user by business impact and by likelihood of breaking. The
enumeration is the agent's job. The ranking is the user's.

Two constraints on the output:

- Each flow is one sentence in product language, from `CONTEXT.md`. "A user adds
  a summarize operation to a query and sees the grain change", not "test
  QueryEditor.vue".
- The inventory is a **bootstrap artifact**. It exists to shard the work across
  agents, and it dies once ticket 08 generates the real one from test titles. Do
  not build anything that has to be kept in sync with it.

## Answer

Inventory: [inventory-draft.md](../inventory-draft.md). **69 flows** across seven
areas, drawn from the 14 routes in `frontend/src2/router.ts`, the operation types
in `types/query.types.ts`, the 9 chart types in `types/chart.types.ts`, and the
area folders. Tiered A / B / C.

**The cut is tier A plus tier B, plus C13 and C15 — 56 of 69, or 81%.**

- **A (24)** is the merge gate. The core loop: source a query, filter, summarize,
  join, mutate, build the four main chart types, assemble a dashboard, create and
  save a workbook, see a shared dashboard as a guest, and honour permissions.
- **B (30)** is the rest of the 80% bar.
- **C13** (number card comparison and sparkline) is pulled up from C because
  `NumberChart.vue` changed 6 times in 3 months — it is a churn hotspot.
- **C15** (share a chart, open the public link) is pulled up because a break
  there is visible to people outside the org.
- **C (13 remaining)** stays out: exotic chart types, script queries, alerts,
  window operations, lineage, and all of Settings.

**Flows split into verify and author.** Demo setup seeds a full workbook — one
query, four charts, one dashboard. Flows that only need to see seeded content
render are **verify** flows: fast, stable, and good at catching render
regressions. Flows that click through creating something are **author** flows:
slow, and where the churn is.

D4, S1 and S2 are verify flows. Every tier A flow is an author flow. The split
only works once ticket 15 lands — a seeded workbook whose charts render empty
verifies nothing.
