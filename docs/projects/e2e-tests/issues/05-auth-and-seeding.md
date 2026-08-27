# 05 — Auth and API seeding

Type: prototype
Status: open
Blocked by: 04

## Question

How does a test arrive at the state it wants to assert on?

Settled already: log in once per role, save `storageState`, reuse it. Build
fixture data through the API, never by clicking.

Open: what the seeding call actually is. `insights/tests/factories.py` holds the
factories the Python suite uses, but Playwright cannot import Python. The
options are a test-only whitelisted endpoint that wraps those factories, plain
REST calls against `insights/api/`, or a CLI step that seeds before the run.

Build a stub that creates a workbook with one query through whichever route
looks cheapest, and react to it. The question the prototype answers is whether
the browser can reuse the existing factories or needs its own.

Also settle which roles get a `storageState`: at minimum an admin and a viewer,
since ticket 14 needs the UI to honour permissions.
