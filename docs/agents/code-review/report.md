# Code review: report

The report format. Whoever writes the report reads this file, and only after every candidate is confirmed or dropped, because a length limit changes what an agent looks for.

## Order

Verdict, owners to decide, scope, guards, defects (must fix, then minor), deferred, dropped. A small PR too. Leave out a heading with nothing under it.

- The verdict is the one line from playbook "For each job", with the count of must-fix findings.
- A change with no findings gets the verdict and one line on what it does. Never make up a finding.
- A re-review opens with one line per earlier finding: resolved with its commit, still open, or ruled on. A ruled finding is not argued again.
- Each failing check is attributed to the change or to the target branch. Only a pass the reviewer can see counts.

## Deciding severity

- The repo's must-fix rules, prior rulings and "Do not flag" are applied once, by whoever writes the report. A reader reports every confirmed defect with a proposed severity. *Readers reached 47 of 73 known defects, reported 17, and argued 30 away.*
- Each finding the filters dropped gets one line under "Dropped", with the rule that dropped it, so the maintainer can overrule it.
- One finding per cause, with its symptoms as evidence, so the report counts causes and not bullets.
- Cut length from prose, never from findings. A finding that survived confirmation keeps its full strength.

## A finding

- It opens with the defect in plain words that a reader can stop at: no paths, identifiers or numbers. Then the `path:line` and a one-sentence fix. Then the proof, collapsed in `<details>`.
- A must-fix finding names its location, the owner or decision it breaks, and the consequence. Its `<details>` hold the trace and the owner. Reader files stay beside the report.
- A suggested fix names the owner of the decision before the change, because the fixer applies it where the suggestion points.
- The visible part stays short: a few lines per must-fix finding, and one line for a minor one, which needs no `<details>`.
- For a risky untested change, name the one test that would settle it, not that coverage is missing.

## Prose

- Simplified Technical English: one point per sentence, active voice, the condition before the instruction, no emoji or filler.
- Explain in concrete code terms that a first-time contributor can check, not in the name of a principle.
- Use a short example where it makes the defect easier to understand, and label an invented one so it is not read as proof.

## Example

Invented, to show the format:

```markdown
**The right change at the wrong layer.** 1 must fix.

**Owners to decide**
- Who names a workbook. The name is stored as a number and compared as text, so this PR converts it at six call sites. An `autoname` method on `Insights Workbook` would make every conversion unnecessary.

**Scope:** the `autoname` method in this PR, and the conversions go with it.

**Guards:** a test that opens a workbook through `get_workbook` as its owner and as a reader it is shared with.

**Must fix**
- **Charts saved before this change render empty.** A new config key ships with no patch. `insights/insights/doctype/insights_chart_v3/insights_chart_v3.json:88`: add a patch to `insights/patches.txt` that sets the key on saved charts.
  <details><summary>Proof</summary>

  Trace, owner and the deciding lines.
  </details>

**Minor**
- The empty state's label wraps at narrow widths. `frontend/src2/charts/ChartEmpty.vue:12`.
```
