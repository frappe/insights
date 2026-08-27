# 03 — Measure the CI floor

Type: task
Status: open
Blocked by: 01

## Question

How long does the cheapest possible browser-test job take in GitHub Actions?

Measure the floor with no fixture data at all: build a site, install Insights,
build the frontend, start the server, run one Playwright test that loads
`/insights` and asserts the login page renders.

Report wall-clock time for each stage separately, so ticket 04's dataset choice
can be priced against a known baseline.

This is the riskiest ticket on the map. If the floor alone is too slow to gate a
pull request, the whole shape changes — a prebuilt image, a nightly run, or a
smaller scope. Resolve it before anything is built on the assumption that CI is
affordable.

The answer records the numbers and the workflow file, not a recommendation.
