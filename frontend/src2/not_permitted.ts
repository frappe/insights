// The client side of Not Permitted.
//
// `insights/not_permitted.py` turns a permission error into an answer the page
// can show. A reader may open a dashboard when one card on it is readable. So
// any endpoint behind that dashboard can meet a table the reader may not read:
// a filter's value list, a card's range, a drill, a table preview. When such an
// endpoint returns an object, it adds `not_permitted` to it. That names the
// doctypes the reader needs read access on, and the user a Run-as-owner chart
// ran as when that is not the reader.
//
// It is an answer, not a failure. The reader cannot fix it, and a retry cannot
// succeed. So the page shows it in place of the content. A page that ignores it
// shows an empty result, and that empty result is false.

import { __ } from './translation'

export type NotPermitted = { doctypes: string[]; run_as?: string }

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
 * line when the server named no doctype. A chart that ran as its owner names
 * the owner, `runAs`: no access of the reader's own would fix it.
 */
export function refusalDetail(doctypes: string[] | undefined, fallback: string, runAs?: string) {
	if (!doctypes?.length) return fallback
	if (runAs) return __("Runs as {0}, who can't read {1}", runAs, doctypes.join(', '))
	return __('Needs read access to {0}', doctypes.join(', '))
}

/**
 * Why the server refused to hand over a dashboard or chart, if it did. A
 * reference that names nothing is Not Found. Content the reader may not read is
 * No Access, and the reader learns nothing else about it.
 */
export type Refusal = 'notFound' | 'noAccess'

export function refusalOf(error: any): Refusal | undefined {
	if (error?.exc_type === 'DoesNotExistError') return 'notFound'
	if (error?.exc_type === 'PermissionError' || error?.exc_type === 'SharedWithRoles')
		return 'noAccess'
}
