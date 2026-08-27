# 05 — Auth and API seeding

Type: task
Status: open
Blocked by: 04

## Question

Build the auth and seeding layer the suite sits on.

This was a prototype ticket. It is now a task: the decisions below are made, and
what remains is to build them.

**Copy `frappe/wiki`'s `e2e/helpers/frappe.ts`.** Ticket 01 found it reusable
verbatim — `createDoc`, `getDoc`, `deleteDoc`, `getList`, `callMethod` over REST
with the CSRF header. Start from it, do not write a new one.

**No test-only endpoint.** `insights/tests/factories.py` cannot be reached from
Playwright, and wrapping it in a whitelisted endpoint would ship a seeding
surface into production code. Gameplan needed a gating pattern for exactly that
risk. Plain REST against `insights/api/` avoids the surface entirely.

**Auth**: a Playwright setup project posts to `/api/method/login`, saves
`storageState` and the CSRF token, and every other project depends on it. Two
roles get a stored state — an admin and a viewer. Ticket 14 needs the viewer.

**Layout**, following wiki:

```
frontend/e2e/
├── .auth/            # gitignored
├── helpers/
├── fixtures/
└── tests/
```

Build fixtures scoped to business actions, not Playwright wrappers — a fixture
that gives a test a workbook with one query over the demo data source, and one
that gives a saved chart. A fixture may create data, but a test must state what
it depends on.

Ticket 07 rewrites `playwright.config.js` to point at this layout. This ticket
establishes it.
