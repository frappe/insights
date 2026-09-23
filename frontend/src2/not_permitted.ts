// The client half of the refusal contract.
//
// `insights/not_permitted.py` turns a refusal into the answer the surface
// draws: a reader is admitted to a dashboard as soon as one card on it is
// readable, so every endpoint behind that dashboard can meet a table this
// reader may not read — a filter's value picker, a card's range, a drill, a
// table preview. An endpoint whose empty answer is a mapping carries this
// beside it, naming the doctypes the reader would need read on.
//
// It is an answer and not a failure: the reader was admitted, they own nothing
// they could fix, and a retry cannot succeed. So a surface reading one of these
// endpoints says so where the picture would be. A surface that ignores it draws
// the refusal as a zero, which is the false empty the whole contract exists to
// remove.

import { __ } from './translation'

export type NotPermitted = { doctypes: string[] }

/** The answer of an endpoint that can refuse. */
export type Refusable<T> = T & { not_permitted?: NotPermitted }

/**
 * Frappe's own name for it, so a reader who wants to know why a surface is
 * blank has a term to look up — in the desk, or from whoever grants it.
 */
export function refusalHeadline() {
	return __('Not Permitted')
}

/**
 * Why it is blank, in the word the site's own permission page uses. The same
 * line for an author and a reader, because neither owns the grant. `fallback`
 * is what the surface says where the boundary named no doctype.
 */
export function refusalDetail(doctypes: string[] | undefined, fallback: string) {
	return doctypes?.length ? __('Needs read access to {0}', doctypes.join(', ')) : fallback
}
