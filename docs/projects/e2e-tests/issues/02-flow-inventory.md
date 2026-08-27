# 02 — The flow inventory and its ranking

Type: grilling
Status: claimed

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
