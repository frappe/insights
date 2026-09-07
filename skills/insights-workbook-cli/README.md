# insights-workbook-cli

A skill that lets a coding agent build, edit and explain Frappe Insights v3 workbooks on
a live site over `frappectl`. It needs no Insights source and nothing installed on the
site.

`SKILL.md` is the procedure. `reference/` is the workbook contract.
`examples/build_workbook.py` is the template the agent copies.

## Install

**Give this page to your agent and ask it to set the skill up.** The steps below are
written for it to follow. Do them by hand if you prefer.

### 1. Get the skill

One directory. Each agent gets a pointer to it, not a copy, so `git pull` is the update
and the skill can never drift from the contract it documents.

```sh
git clone https://github.com/frappe/insights
SKILL=$PWD/insights/skills/insights-workbook-cli
```

### 2. Point the agent at it

Find the agent's skills directory and link the skill into it:

| Agent | Directory |
|---|---|
| Claude Code | `~/.claude/skills` |
| Codex | `~/.codex/skills` |

```sh
mkdir -p ~/.claude/skills
ln -s "$SKILL" ~/.claude/skills/insights-workbook-cli
```

The agent reads the `description` in `SKILL.md` and offers the skill when a task fits.

An agent with no skill loader takes a prompt instead. Write it wherever that agent keeps
its prompts, with the real path in place of `$SKILL`:

> Read `$SKILL/SKILL.md` and follow it. Read the files under `$SKILL/reference/` when it
> tells you to.

### 3. Give it a site

The skill needs a `frappectl` profile. **Make it yourself.** The skill tells the agent
not to run `auth` commands, so it will not do this step for you.

```sh
uv tool install frappectl
frappectl auth login https://your-insights-site --name your-site
```

The profile's user is who the agent acts as. It sees the workbooks, data sources and
tables that user can see, and nothing else. To let the agent do less, give it a profile
for a user who can do less.

## Check it worked

Ask the agent to list the workbooks on the site. It should reach for the skill, and the
first call it makes should be `frappectl -s <your-site> auth whoami`.
