# Runtime version policy

Type: grilling
Status: open

## Question

Ticket 02 settled that framework provides Vue and frappe-ui as page singletons
and Insights builds against them as externals. That makes version ownership a
contract question.

- How does Insights declare which frappe-ui version it needs, and how is that
  checked?
- What happens on skew — framework ships a newer frappe-ui than Insights was
  built against, or older? Fail loudly, degrade, or refuse to mount?
- Does Insights' release cadence now follow framework's frappe-ui version, and
  is that acceptable?
- Does the singleton rule reach Vue-frontend apps (CRM-class), which bundle
  their own runtime today, or is it desk-only?
- Which packages are in the shared set — Vue, frappe-ui, echarts, anything
  else?

Consequence already visible: Insights ends up with two build targets from one
source — the standalone SPA at `/insights`, which bundles everything, and the
desk island, which externalises the shared set.

This ticket gates the build and mount-API tickets.
