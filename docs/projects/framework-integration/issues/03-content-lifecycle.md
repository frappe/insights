# Content lifecycle: author → ship → customize

Type: grilling
Status: open

## Question

The producer side of the contract: how a dashboard/chart gets from an app
developer's hands into their app, and what happens when users touch it.

- Authoring: in Insights' builder, then export? What exactly exports?
- Shipping: what form in the app's codebase (folder of files? which hook)?
- Customization: what happens when a user edits shipped content — and what
  happens on app update?

Starting position (Saqib, from charting — probably a short ticket): author in
builder → export, ship as files in an app folder, customization =
duplicate/fork (no in-place merge; avoids conflict management / a full VCS).

Constraint to respect: the export format must stay stable — a future
code-first authoring API would emit the same format (see map fog).
