# 01 — How other Frappe apps run browser tests in CI

Type: research
Status: claimed

## Question

Insights is not the first Frappe app to want browser tests. Several sibling apps
already run them in GitHub Actions against a real site.

Find out, for `frappe/helpdesk`, `frappe/crm`, `frappe/gameplan`,
`frappe/builder`, and `frappe/frappe` itself:

- Which harness each uses, and whether any moved between harnesses.
- How the CI workflow builds the site, and how long that takes.
- How tests authenticate, and whether they seed data through the API.
- What the fixture data is, and where it comes from.
- Whether the suite gates pull requests or only runs nightly.
- Any recorded flakiness or maintenance complaint.

The point is to copy a working recipe rather than derive one. Report what is
directly reusable, what is Insights-specific, and any recipe that was tried and
abandoned.
