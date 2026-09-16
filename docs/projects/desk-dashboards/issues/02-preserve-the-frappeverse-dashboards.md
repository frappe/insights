# Preserve the frappeverse dashboards

Type: task
Status: open
Repo: insights

## Question

The dashboards reviewed at frappeverse exist only in the `demo.erpnext.localhost` database: workbooks 47 Business Overview, 49 Purchase & Payables, 54 Receivables, 55 Stock, 56 HR, 57 Selling. No branch holds them. A dropped site loses them.

Export each as `workbook.json` into `docs/projects/desk-dashboards/assets/<slug>/` using the existing template export, so the mechanism ticket can read them and the review ticket has a baseline. Note per workbook: chart count, source doctypes, anything that failed to export.

This is preservation, not the shipping format. The shipping format is ticket 03's decision.
