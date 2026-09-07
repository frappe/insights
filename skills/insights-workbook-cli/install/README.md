# Install

One skill directory. Each agent gets a pointer to it, not a copy.

Clone the Insights repository, or copy this directory out of it:

```sh
git clone https://github.com/frappe/insights
SKILL=$PWD/insights/skills/insights-workbook-cli
```

`git pull` is the update. The skill and the contract it documents ship together, so
they cannot drift apart.

## Claude Code

```sh
mkdir -p ~/.claude/skills
ln -s "$SKILL" ~/.claude/skills/insights-workbook-cli
```

Claude reads the `description` in `SKILL.md` and offers the skill when the task fits.

## Codex

Codex 0.46 has no skill loader. It has prompt files:

```sh
mkdir -p ~/.codex/prompts
sed "s|SKILL_DIR|$SKILL|g" "$SKILL/install/codex-prompt.md" \
  > ~/.codex/prompts/insights-workbook.md
```

Then run `/insights-workbook <what you want>`.

A Codex that reads `SKILL.md` takes the directory instead:

```sh
mkdir -p ~/.codex/skills
ln -s "$SKILL" ~/.codex/skills/insights-workbook-cli
```

## Site access

The skill needs a `frappectl` profile for the Insights site. Make one yourself — the
skill tells the agent not to run `auth` commands.

```sh
uv tool install frappectl
frappectl auth login https://your-insights-site --name your-site
```

The profile's user is who the agent acts as. It sees the workbooks and data sources
that user can see, and nothing else.
