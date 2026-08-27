# 08 — Generate the inventory from the test titles

Type: task
Status: open
Blocked by: 02, 07

## Question

Make the flow inventory impossible to drift.

Generate `frontend/tests/FLOWS.md` from the Playwright test titles, using the
built-in JSON reporter. Add a CI check that regenerates it and fails if the
committed copy differs — the same shape as a lockfile check.

Then **delete ticket 02's bootstrap inventory.** Two lists of flows is the
failure this ticket exists to prevent. If the bootstrap list holds anything the
generated one does not, that gap is uncovered flows, and it belongs in a ticket
rather than in a document.
