# A second editor is invisible

Type: task
Status: ready-for-agent

## Question

Two people open the same chart. One changes the x-axis and the autosave lands. The other's browser never hears about it. The other then changes a title, and their autosave carries their whole document — including the old x-axis. The first change is gone, and neither person is told.

Three things make this possible, and all three were read in the framework and in `resource.ts`:

1. **The client never sends `modified`.** It is in `metaFields` (`frontend/src2/helpers/resource.ts:307`) and stripped from every payload.
2. **`frappe.client.set_value` cannot check a version.** It does `frappe.get_doc(doctype, name)` — a fresh read — then applies the fields and saves (`frappe/client.py:215`). So `check_if_latest` compares the fresh read against itself and always passes. `modified` is a framework default field, so `set_value` strips it from the payload as well. No timestamp check can ride on this endpoint.
3. **Nothing refreshes an open document.** `setupRealtimeUpdates` is commented out (`frontend/src2/helpers/resource.ts:258`) and `loadDoc` runs once, when the store is created.

Result: last write wins, at whole-document granularity, silently.

## What desk does

Four layers, none of which merge:

- **The write carries the version.** `frappe.desk.form.save.savedocs` sends the whole document, `modified` included, so `check_if_latest` throws `TimestampMismatchError` (`frappe/model/document.py:1404`).
- **Realtime tells you first.** Every save publishes `doc_update` with the new `modified`, scoped to the doctype and name (`frappe/model/document.py:1949`). The client branches on whether the form is dirty: clean reloads silently, dirty shows a headline with a Refresh button (`frappe/public/js/frappe/model/model.js:154`). Two guards matter — it ignores the event while it is saving, and it ignores an answer whose `modified` it already holds.
- **Presence.** `doc_viewers` draws the avatars of everyone with the document open.
- **No merging.** The loser refreshes and loses their edits.

Desk can afford that last line because it has **no autosave**. A form stays dirty until Ctrl+S, so a person who is told to refresh knows what they are holding.

Insights autosaves every 1500 ms. That inverts the two cases in our favour: the document is almost always clean when the event arrives, so desk's silent-reload path becomes the normal one and the dirty-banner path becomes rare.

## What to build

**1. Realtime, clean-reload only.** Subscribe to `doc_update` for the open document. `attachRealtimeListener` already exists in `frontend/src2/helpers/index.ts`, and the call is already written and commented out in `resource.ts`. Copy desk's two guards: ignore the event while `isSaving`, and ignore it when `data.modified` equals the `modified` already held. Reload only when the document is not dirty. A dirty document sets a flag and waits.

**2. A version check on the write.** Realtime cannot close the window between another person's save and the event arriving. A thin endpoint does:

```python
@frappe.whitelist()
def set_value(doctype: str, name: str, fieldname: dict, modified: str | None = None):
    if modified:
        # for_update holds the row until this request commits, so the check and
        # the write cannot be interleaved
        current = frappe.db.get_value(doctype, name, "modified", for_update=True)
        if str(current) != str(modified):
            frappe.throw(_("This {0} was changed elsewhere.").format(doctype), frappe.TimestampMismatchError)
    return frappe.client.set_value(doctype, name, fieldname)
```

Point `DEFAULT_API.update` at it and pass `modified` beside the fields. On `TimestampMismatchError` the client turns `autoSave` off for that document and offers two buttons: **Reload**, which runs `loadDoc()`, and **Copy my version**, which writes the local document to the clipboard through the `export` path that already exists. The second one is what makes losing the write acceptable.

**3. Presence.** `doc_viewers` avatars, on the workbook. Cheapest of the three and it prevents more collisions than either of the others.

## What not to build

- **No merging.** The single-author assumption is the decision, not an omission.
- **Do not switch to `frappe.client.save` to get the framework's check for free.** It rebuilds the document from the client's dict, so any field the client does not hold is dropped. The thin endpoint is six lines and drops nothing.
- **Do not fix this by writing fewer fields.** Per-field writes are the command surface, which is a separate and larger decision. This ticket makes the current write safe.

## Two things to check while building

- Realtime dies silently under `yarn dev`, because socket.io auth loops through vite. Test on the bench port.
- `publish_realtime` with a doctype and a name sends to a room. Confirm a user without read access on the chart does not receive the event before relying on it.

## Done when

- Two browsers, same chart. One edits, the other's card follows without a reload.
- One browser held offline through an edit, then made to write, gets the message and keeps its version through Copy.
- Neither case writes over the other silently.
