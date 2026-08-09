# Query building moves server-side

Type: grilling
Status: open

## Question

The direction: the server owns the computation of queries, and the client
holds only declarative state. Two slices are already on this path:

- [Ticket 27](27-chart-query-derivation-owner.md) (resolved) — the server
  derives a chart's query from `config` at execution time. The client keeps
  zero derivation. The Python deriver is route step 1.
- [Ticket 11](11-drill-down-interaction.md) — the drill-down layer for read
  surfaces. Operations never reach a viewer client, so the drill fork
  (resolve effective operations, slice before the last summarize/pivot,
  apply segment filters — today `makeDrillDownQuery` in
  `frontend/src2/query/query.ts`) must run on the server.

The open question is the rest: what becomes of the client-side operations
layer in `frontend/src2/query/` — the builder's operation editing, undo and
history, live preview. That is the authoring surface, and it is a bigger
move than the two slices above.

Sequencing rule: this ticket does not block ticket 11. Each drill decision
is checked against "does this paint the server-side move into a corner" —
the descriptor-based contract advances the move rather than blocking it.

## Acceptance criteria

- [ ] A ratified owner for each remaining client-side query computation,
      or an explicit decision to keep it client-side and why
- [ ] The builder's editing loop stated: what the client sends, what the
      server answers, where undo/history lives
- [ ] A route in shippable steps, with tickets 27 and 11 named as the
      first two
