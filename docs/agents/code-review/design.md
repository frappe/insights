# Code review: design stage

Read at the design stage of `/iris-code-review`, after `brief.md`.

## Foundation

The headline checks. Each is a `Concerns` finding, even when the code works — a pattern
that lands under merge pressure becomes the convention. Name the cheaper fix and the
layer that owns it.

- **The case, not the cause.** The fix patches call sites instead of removing the
  mismatch that creates them. *Precedent: a fix stringified a workbook name at every
  boundary; the cause was an `autoincrement` doctype, and one `autoname` method removed
  the convention.* *"i don't just want to fix these once, i want to fix them such that the
  class of issue never happens"*.
- **A second implementation.** A new path beside one that exists. *"there are 4 surfaces
  now to consume a dashboard … which i don't like"*, *"i'd prefer only one foundation, i
  don't like hybrid."* Two components doing one job, two doc sets, two clients — same
  finding.
- **A branch that could be assumed away.** Ask what removing it buys. *"if we just
  eliminate the branch where insights doesn't exists. what does this lead to?"* A guard is
  one condition, not a stack of special cases.
- **A convention every future call site must remember.** *"else everyone has to remember
  to enable this check, which is worse"*. Put the rule in the type, the doctype, or the
  one function all callers already pass through. Prefer a good default over a flag.
- **Machinery before a need.** A parameter, hook, flag, registry or abstraction no ticket
  asks for. *"looks like too much machinery?"*, *"we don't need to be that generic, i
  don't see ourselves wanting someone else to define a dashboard renderer"*. Also flag
  any artifact that must be hand-maintained in parallel with code — it will drift.
- **Hand-rolled where a known tool exists.** A parser, picker, scheduler or helper the
  framework, frappe-ui, or a library already in the bundle provides. Grep for real usage
  first. *"in general don't spin up custom utils/functions if framework provides it"*.
  *Precedent: a hand-written splitter was replaced with the CodeMirror Python parser
  already shipped for `Code.vue`.* Promote what exists; do not invent.
- **A new dependency for a small job.** A package added to `frontend/package.json` or
  `pyproject.toml` needs the job named, and needs a reason nothing in the bundle does it.
  The frontend ships to the browser, so a dependency there costs every user. Measure the
  cost rather than argue it.
- **The constraint was never read.** A workaround built on a framework default without
  reading its implementation or the call path. Defaults are usually parameters we own.
  *Precedent: a client-side scheduler shipped before anyone read `@concurrent_limit()`,
  which takes a `wait_timeout` we set.*
- **Wrong layer.** Say which layer owns the fix, even when the symptom is elsewhere
  and the fix crosses a repo. An app-side workaround for a frappe-ui or framework gap is
  a finding — the local patch is the incremental route, not the destination, so the
  upstream issue or PR goes with it. Settle who owns the data, the engine and the
  rendering before the integration code.
- **Bent to the current implementation.** The design follows what exists or what the
  framework happens to do, not what the feature should be. Name the ideal shape, then
  accept the incremental route to it. *"i don't want us to be tied or anchor to the
  current implementation, feel free to think of a better and more pure design"*.
- **Seam purity, both directions.** Insights builds on frappe-ui and the framework; it
  must not push its own needs into them. *"the feature shouldn't depend on what the
  frappe app wants, it should depend on the convention v2 chart is built on"*. Shared
  code designed around its first consumer is the same finding. Purity yields to
  simplicity when the simpler design needs the coupling — name the coupling and ask
  whether an uncoupled design is simpler.
- **Bolted on.** A capability added beside a resource rather than made part of it. *"right
  now it feels bolted on, and not first class"*, *"does this whole thing feel like fixes
  bolted on to one quirk on top of another?"*.
- **Clever, or foreign.** Fewer lines bought with indirection, or code that does not look
  like the framework wrote it. *"i hate being smart about the code for less lines of
  code"*, *"the whole thing looks foreign and not 'frappe' style"*. Simplicity beats an
  optimisation; strictness is not traded for readability.
