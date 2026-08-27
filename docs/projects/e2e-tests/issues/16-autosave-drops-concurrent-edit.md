# 16 — An autosave answer drops every edit made while it was in flight

Type: bug
Status: open
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
