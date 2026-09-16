# How desk reaches a standard dashboard

Type: grilling
Status: open
Blocked by: 03
Repo: erpnext, insights

## Question

Every ERPNext dashboard is reached from one workspace sidebar item (`link_type: Dashboard`, `link_to: Accounts` and so on), routed to `dashboard-view/<name>`, which mounts `insights.dashboard` when the desk `Dashboard` document carries `insights_dashboard`. Nothing sets that field today.

Options on the table: the shipped content names the desk Dashboard it stands in for and the sync sets the pointer on ERPNext's existing document; ERPNext ships new Dashboard documents for the purpose and repoints the sidebar item; the sidebar item links the Insights dashboard by another type. Decide which, who writes it, and what a site without Insights sees. Business Overview, which has no ERPNext dashboard, is the test case.
