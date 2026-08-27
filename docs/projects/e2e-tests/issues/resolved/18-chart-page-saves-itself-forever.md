# 18 — A chart page saves itself about every 1.5 seconds, forever

Type: bug
Status: resolved
Found by: 17 (suite stability)
Related: 16

## What happens

Open any Chart whose dimension is not a date. The page sends
`frappe.client.set_value` about every 1.5 seconds, for as long as it stays open,
with a payload that never changes.

Measured on a seeded Bar chart over `order_status`. Four identical saves in the
first seven seconds, and the stored document is byte for byte what it was.

## Why

Three pieces, each harmless alone.

1. `DimensionPicker.vue` runs a `watchEffect` that reads the granularity options
   for the dimension's data type. A String column has none, so it assigns
   `dimension.granularity = undefined` — unconditionally, on every run.

2. `copy()` in `frontend/src2/helpers/index.ts` is
   `JSON.parse(JSON.stringify(...))`, and a JSON clone drops a key whose value
   is `undefined`. `originalDoc` in `helpers/resource.ts` is always a `copy()`,
   so `doc` keeps the key and `originalDoc` does not.

3. `isDirty` is `!isEqual(doc.value, originalDoc.value)`, and es-toolkit's
   `isEqual` counts keys. The document is therefore dirty forever.

With `enableAutoSave` on, that is a loop: save → the answer replaces `doc` →
the `watchEffect` writes `undefined` again → dirty again.

A date dimension gets a real granularity, so a Line chart over
`order_purchase_timestamp` does not loop. Every Bar, Row, Donut and Table chart
over a text column does.

## What it costs

- **Every open chart writes to the site continuously.** One reader with a
  dashboard open is a steady write load that nothing asked for.
- **Ticket 16 becomes permanent on a chart page.** Ticket 16 is about edits
  dropped while a save is in flight, and its window is one round trip. Here
  there is always a save in flight to fall into, so no ordering of clicks
  escapes it. This is what the end-to-end suite could not work around.
- **Version rows.** Each save writes the same document, so whether it also
  writes history is worth checking.

## The fix

Comparing clones closes the whole class:

```ts
const isDirty = computed(() => !isEqual(copy(doc.value), originalDoc.value))
```

`originalDoc` is already a clone, so this compares like with like and an
`undefined` key stops counting. The same change was made on the
`docs/framework-integration-map` branch on 2026-08-13, for the same fault in the
same picker, and it is not on `develop`.

Worth doing as well, and independently: a config form should `delete obj.key`
rather than assign `undefined`. A config is stored as JSON, so a key with no
value is a key the next load will not have.

## How to see it

Load a Bar chart over `order_status`, watch the network panel, and read the
`set_value` payloads. They are identical. The server shows nothing, because the
document never changes, so no `Version` row is written and `modified` moves
without anything moving with it.

## Answer

Fixed by cherry-picking `b32ee6fc2 fix(frontend): measure a document's dirtiness
against a clone`, which was written on `docs/framework-integration-map` on
2026-08-13 and never reached `develop`.

It changes `isDirty` to compare `copy(doc.value)` against `originalDoc`, so both
sides are clones and an `undefined` key stops counting. It also deletes a
granularity key rather than assigning `undefined`.

**Measured before and after.** Two full suite runs sent **56** `set_value` calls
in total, 28 per run — one per chart the suite creates. The server log had
accumulated 5054 before the fix. The loop is gone.

This fix belongs on `develop` on its own merits, independent of the test suite.
It is a continuous write from every open chart page, for every user.
