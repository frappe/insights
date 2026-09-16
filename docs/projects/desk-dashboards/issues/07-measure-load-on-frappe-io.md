# Measure load on frappe.io

Type: task
Status: open
Blocked by: 06
Repo: insights

## Question

Once the six dashboards are on frappe.io, record per dashboard and per chart: query time, rows scanned, anything near the 60 s timeout. Live queries against the production database, no snapshots. Note which charts need a lighter source (the accounting AR/AP query already moved from GL Entry to Payment Ledger Entry for this reason) before the review sitting.
