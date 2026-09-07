# Agent skills

Skills for AI coding agents that work against a live Insights site.

| Skill | What it does |
|---|---|
| [insights-workbook-cli](insights-workbook-cli/) | Build, edit and explain workbooks over `frappectl` |

A skill is one directory: `SKILL.md` is the procedure, `reference/` is the contract it
authors against, and `README.md` says how to point an agent at it.

The contract files live here rather than beside the agent that reads them, so a change
to an operation type or a chart config travels in the same pull request as the code
that made it.
