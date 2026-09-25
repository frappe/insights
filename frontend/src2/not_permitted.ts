// The client side of Not Permitted.
//
// `insights/not_permitted.py` turns a permission error into an answer the page
// can show. A reader may open a dashboard when one card on it is readable. So
// any endpoint behind that dashboard can meet a table the reader may not read:
// a filter's value list, a card's range, a drill, a table preview. When such an
// endpoint returns an object, it adds `not_permitted` to it. That names the
// doctypes the reader needs read access on.
//
// It is an answer, not a failure. The reader cannot fix it, and a retry cannot
// succeed. So the page shows it in place of the content. A page that ignores it
// shows an empty result, and that empty result is false.

import { __ } from './translation'

export type NotPermitted = { doctypes: string[] }

/** The answer of an endpoint that can refuse. */
export type Refusable<T> = T & { not_permitted?: NotPermitted }

/**
 * Frappe's own term, so the reader has a word to look up or to ask an admin
 * about.
 */
export function refusalHeadline() {
	return __('Not Permitted')
}

/**
 * Uses the wording of the site's permission page. An author and a reader get
 * the same line, because neither of them can grant access. `fallback` is the
 * line when the server named no doctype.
 */
export function refusalDetail(doctypes: string[] | undefined, fallback: string) {
	return doctypes?.length ? __('Needs read access to {0}', doctypes.join(', ')) : fallback
}
