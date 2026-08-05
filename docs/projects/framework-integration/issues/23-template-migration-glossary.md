# 23 — Template migration and glossary

Type: task
Status: ready-for-agent
Blocked by: 21, 22
Spec: [spec-insights-foundation.md](../spec-insights-foundation.md), "Migration"

## What to build

The old shipping channel retires. One mechanism remains.

- The four shipped workbook templates re-export into the bundle format and
  sync as standard content.
- Existing imported template copies become user documents — they were
  user-editable, so they are forks by definition.
- The gallery's "import" becomes "duplicate", reusing ticket 22's action.
- The version/checksum update model (`imported_version`,
  `imported_checksum`, warn+manual updates, auto-apply on migrate) retires.
- `CONTEXT.md` gains the new glossary entries: Bundle, Standard content,
  Slug. The Template entry is revised to describe the bundle channel.

## Acceptance criteria

- [ ] The four templates ship as bundles and appear as standard content
      after migrate
- [ ] A site with imported template copies migrates cleanly: copies become
      user documents and keep working
- [ ] The gallery offers "duplicate" and no import ceremony remains
- [ ] The version/checksum machinery is deleted, tests included
- [ ] `CONTEXT.md` records Bundle, Standard content, and Slug, and the
      revised Template entry
