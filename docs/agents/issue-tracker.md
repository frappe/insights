# Issue tracker: Local Markdown

Issues and specs (you may know a spec as a PRD) for this repo live as markdown
files in `docs/projects/`.

`docs/` is ignored by default and individual efforts are allowlisted in
`.gitignore` as they are published. So an effort is either **published** (in the
repo, reviewable in pull requests) or **local-only** (working notes that never
leave the machine). Check `.gitignore` before assuming a path is committed.

GitHub Issues (frappe/insights) is the public/community queue, not this tracker.
Don't create or triage GitHub issues unless explicitly asked.

## Conventions

- One effort per directory: `docs/projects/<effort-slug>/`
- The spec is `docs/projects/<effort-slug>/spec.md`
- Implementation issues are one file per ticket at
  `docs/projects/<effort-slug>/issues/<NN>-<slug>.md`, numbered from `01` —
  never a single combined tickets file
- Triage state is recorded as a `Status:` line near the top of each issue file
  (see `triage-labels.md` for the role strings)
- Comments and conversation history append to the bottom of the file under a
  `## Comments` heading
- Concluded efforts move to `docs/archive/`

## When a skill says "publish to the issue tracker"

Create a new file under `docs/projects/<effort-slug>/` (creating the directory
if needed).

## When a skill says "fetch the relevant ticket"

Read the file at the referenced path. The user will normally pass the path or
the issue number directly.

## Wayfinding operations

Used by `/wayfinder`. The **map** is a file with one **child** file per ticket.

- **Map**: `docs/projects/<effort>/map.md` — the Notes / Decisions-so-far / Fog body.
- **Child ticket**: `docs/projects/<effort>/issues/NN-<slug>.md`, numbered from `01`,
  with the question in the body. A `Type:` line records the ticket type
  (`research`/`prototype`/`grilling`/`task`); a `Status:` line records `claimed`/`resolved`.
- **Blocking**: a `Blocked by: NN, NN` line near the top. A ticket is unblocked
  when every file it lists is `resolved`.
- **Frontier**: scan `docs/projects/<effort>/issues/` for files that are open,
  unblocked, and unclaimed; first by number wins.
- **Claim**: set `Status: claimed` and save before any work.
- **Resolve**: append the answer under an `## Answer` heading, set `Status: resolved`,
  then append a context pointer (gist + link) to the map's Decisions-so-far in `map.md`.
- **Research findings**: land in `docs/projects/<effort>/research/`, linked from
  the ticket's answer.
