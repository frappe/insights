// Where a reader's filter choices live between visits. Nothing on the server
// holds per-user view state, so the browser keeps it — scoped by user, because a
// shared workstation must not hand one person's view to the next.

import session from '../session'
import type { FilterValues } from '../types/workbook.types'

function key(dashboard: string) {
	return `insights:dashboard-filters:${session.user.email || 'Guest'}:${dashboard}`
}

export function readFilters(dashboard: string): FilterValues {
	try {
		return JSON.parse(localStorage.getItem(key(dashboard)) || '{}')
	} catch {
		// a hand-edited or half-written entry is not worth a broken page
		return {}
	}
}

export function writeFilters(dashboard: string, filters: FilterValues) {
	if (Object.keys(filters).length) {
		localStorage.setItem(key(dashboard), JSON.stringify(filters))
	} else {
		localStorage.removeItem(key(dashboard))
	}
}
