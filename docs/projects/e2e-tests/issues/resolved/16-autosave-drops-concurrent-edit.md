# 16 — An autosave answer drops every edit made while it was in flight

Type: bug
Status: fixed
Found by: 17 (suite stability)

## What happens

`useDocumentResource` in `frontend/src2/helpers/resource.ts` autosaves 1.5
seconds after a document's first unsaved change. `updateDoc` sends the document
as it stood when the request left, and `updateDocState` replaces the whole
document with the answer:

```ts
function updateDocState(newDoc: any) {
	doc.value = transformFn({ ...newDoc }) as UnwrapRef<T>
	originalDoc.value = copy(doc.value)
	docname.value = newDoc.name
}
```

Every edit made between the request leaving and the answer arriving is
overwritten. Nothing tells the user. The document is not even marked dirty
afterwards, because `originalDoc` is set from the same answer, so the next
autosave has nothing to send.

The window is one network round trip, and it widens with load.

## What it looks like

Three symptoms, one cause. Two were found independently, by two agents, before
the cause was read.

1. **The chart builder snaps a picker back.** Ticket 10 recorded "a chart config
   edit made during a refresh is dropped", about one run in three. The measure
   picker is the worst case: picking an aggregation and picking its column are
   two edits, and losing the first tears down the list the second needs.
2. **A dashboard item editor keeps an orphan.** Ticket 11 recorded this as its
   bug 2. `Dashboard.isEditingItem` matches by `items.indexOf(item)`, so once
   `doc.items` is a new array the open editor edits an item the dashboard no
   longer holds. Its Save writes nothing.
3. **A chart sort direction does not flip.** Seen once in the suite's first
   stability runs. The toggle lands while a save is in flight.

## Why the suite cannot record it

A characterization test states what the app does. This does something different
each run, so no assertion states it.

The suite works around it instead, and `frontend/e2e/AGENTS.md` carries the rule
under "Never wait in the middle of an edit": two edits of one interaction run
back to back, and an unavoidable wait goes before the first edit rather than
between two. That keeps every edit of an interaction on one side of the save.

The workaround holds only while an interaction is short. It is not a fix.

## What a fix would look like

The answer to a save is not news. Merge it, or apply only the fields the request
sent, rather than replacing the document. Alternatively, keep the edits made
during the flight and replay them onto the answer. Either removes the class.

The dashboard editor's `indexOf` identity is a second, smaller fault. An item
that carried its own id would survive an array swap.

## Reopened

Closing this was wrong. The quarantined test passed, and I read that as the bug
being fixed. It is not.

`updateDocState` in `frontend/src2/helpers/resource.ts:173` still replaces the
whole document with the save answer. An edit made while a save is in flight is
still thrown away, with no error and no toast. What the cherry-pick removed is
the *perpetual* save on a chart page, so the window is now one round trip
instead of always open. Narrower is not closed.

`frontend/e2e/AGENTS.md` still teaches four shapes to dodge the window, and the
suite still carries about 66 lines written around it. That is the proof it is
open.

The fix this ticket asks for stands: merge the save answer, or apply only the
fields the request sent, rather than replacing the document.

## Earlier note, kept for the record

Fixed by cherry-picking `b32ee6fc2 fix(frontend): measure a document's dirtiness
against a clone` onto this branch.

Ticket 18 explains why this window was permanent on a chart page. With the loop
gone, there is no save perpetually in flight to fall into. The dashboard filter
flow was quarantined against this ticket and now passes: three runs alone, then
three full-suite runs at 57 tests. The `@quarantine` tag is removed, and the
suite has none left.

## Fixed

`updateDocState` takes the clone the write carried and compares it against the
document as it stands when the answer lands. A field that no longer matches was
edited in flight, so the newer value wins over the answer. `originalDoc` still
takes the answer whole, which leaves the document dirty, and `saveDoc` writes
the kept edit straight after. That second write ends the chain, because it
carries the kept edit and so cannot differ from it.

`insertDoc` takes the same route. A load still replaces the document, which is
what a load means.

Two defaults moved with it, because the suite mirrored them by hand.
`transformChartDoc` now sets `y_axis.stack` for a Bar chart, and the dashboard
transform sets `layout.moved`. Both were written by the page on mount, which
made a freshly seeded document dirty before the user touched it.

`frontend/e2e/AGENTS.md` loses the four dodging shapes, and the suite loses the
mirrored defaults. "A user sorts a chart" and "a user flips that sort" are one
flow again, and that flow asserts between the two edits.
