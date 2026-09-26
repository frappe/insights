// Keeps a reader's filter choices between visits. The server stores no per-user
// view state, so the browser keeps them. The key includes the user, so a shared
// computer does not show one person's filters to the next.

import session from '../session'
import type { FilterValues } from '../types/workbook.types'

function key(dashboard: string) {
	return `insights:dashboard-filters:${session.user.email || 'Guest'}:${dashboard}`
}

export function readFilters(dashboard: string): FilterValues {
	try {
		return JSON.parse(localStorage.getItem(key(dashboard)) || '{}')
	} catch {
		// a hand-edited or half-written entry must not break the page
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
