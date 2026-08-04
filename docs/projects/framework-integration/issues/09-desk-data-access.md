# Data access for desk-rendered content

Type: grilling
Status: open

## Question

Every `@insights_whitelist` endpoint requires the `Insights User` role (ticket
01). An ordinary desk user viewing an embedded chart in a workspace or a
dashboard page has no such role, so the data path needs a story that does not
assume one.

- What does a desk user need to view an embedded chart — a role, a permission
  on the chart document, or nothing beyond access to the page?
- How is the already-decided author-mode vs viewer-mode choice declared on
  content, and enforced when the request arrives from a desk page rather than
  the Insights app?
- Does viewing embedded content imply any access to Insights itself (opening
  the workbook, drilling into the underlying query)?
- What does drill-down expose — the chart's rows only, or the query behind it?

Constraint: the answer must not require site admins to grant `Insights User`
broadly, since that would widen access to the Insights app as a side effect of
embedding a chart.
