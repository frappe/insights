import { isEqual } from 'es-toolkit'
import { copy } from './index'

/**
 * The document to hold after a write, given the three things that describe it.
 *
 * A write's answer is a receipt: it repeats what the write carried. Only what it
 * says differently is news — `modified`, a field the server computed, a field
 * this client may not write. So a field is taken from the answer when the answer
 * differs from what was sent, and kept otherwise.
 *
 * Kept means the object itself, not an equal copy. The server sorts the keys of
 * every JSON field it stores, so an answer holding the same config comes back
 * holding it in a different order. Anything below that reads the config as a
 * string — a memo key, a request signature — reads that as an edit and acts on
 * it.
 *
 * @param current what is on screen now, without the framework's own fields
 * @param answer the document the server sent back, already transformed
 * @param sent the deep clone the write carried
 */
export function mergeWriteAnswer<T extends Record<string, any>>(
	current: Record<string, any>,
	answer: T,
	sent: Record<string, any>,
): T {
	for (const field of Object.keys(current)) {
		// An `undefined` value is dropped by `copy`, so keeping one here would
		// make the document dirty forever. Let the answer win.
		const held = copy(current[field])
		if (held === undefined) continue

		// The field moved after the write left, so the newer value wins.
		if (!isEqual(held, sent[field])) {
			;(answer as any)[field] = current[field]
			continue
		}

		// The answer only repeats what the write carried, so nothing here is
		// news. Keep what is already on screen.
		if (isEqual(copy(answer[field]), sent[field])) {
			;(answer as any)[field] = current[field]
		}
	}

	return answer
}
