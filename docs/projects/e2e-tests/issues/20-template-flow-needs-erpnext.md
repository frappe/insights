# 20 — A workbook template flow has no entry point on the test site

Type: task
Status: open
Blocked by: 08

## Question

Cover W8, "a user opens a workbook template and it materializes". Ticket 12
found it has no entry point, so it is the one flow inside the 80% cut that a
test cannot reach today.

Every template shipped under `insights/workbook_templates/` declares
`required_apps: ["erpnext"]`. `test.insights.localhost` and the CI site both run
`frappe` and `insights` only. `get_workbook_templates` therefore returns an
empty list, the Library button never renders, and the flow has nothing to click.

The flow itself is ready to write. Only the site is missing.

Decide which of these buys the flow at the lower cost, then build it:

1. **Install ERPNext on the test site and in CI.** It is the real path a user
   takes, so the test would cover the real templates. It adds an app install to
   the CI job, which ticket 01 measured at 2 to 3 minutes for Insights alone.
2. **Ship a template with no `required_apps`.** One template over the demo Data
   Source would make the Library render everywhere. It is a product change, not
   a test change, and it needs a reason beyond testing to be worth it.
3. **Seed a template from the test.** Check whether the
   `insights_workbook_templates` hook can take a template a test registers, and
   whether that is honest enough to count as covering the flow.

Option 1 is the only one that covers what a user actually does. Measure its cost
in CI before ruling it out.
