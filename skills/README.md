# Agent skills

Skills for AI coding agents that work against a live Insights site.

| Skill | What it does |
|---|---|
| [insights-workbook-cli](insights-workbook-cli/) | Build, edit and explain workbooks over `frappectl` |

A skill is one directory. `SKILL.md` is the procedure. `reference/` is the contract it
authors against. `README.md` says how to point an agent at it.

The contract files live here, not beside the agent that reads them. A change to an
operation type or a chart config then travels in the same pull request as the code that
made it.
