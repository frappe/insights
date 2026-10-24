# Agent skills

Skills for AI agents that work against a live Insights site.

| Skill | What it does |
|---|---|
| [frappe-insights](frappe-insights/) | Build, edit and explain workbooks over the site's assistant, MCP or `frappectl` |
| [insights-workbook-cli](insights-workbook-cli/) | Deprecated, to be removed. The same over `frappectl` only |

A skill is one directory. `SKILL.md` is the procedure. `reference/` is the contract it
authors against.

The contract files live here, not beside the agent that reads them. A change to an
operation type or a chart config then travels in the same pull request as the code that
made it.

`insights-workbook-cli` links `reference/` and `examples/` to `frappe-insights`, so both
skills read the same files.
