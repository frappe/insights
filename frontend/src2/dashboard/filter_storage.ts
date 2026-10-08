// Keeps a reader's filter choices between visits. The server stores no per-user
// view state, so the browser keeps them. The key includes the user, so a shared
// computer does not show one person's filters to the next.

import session from '../session'
import type { FilterValues } from '../types/workbook.types'

// A filter the reader cleared is stored as null, so its default does not come
// back. A filter missing from storage, such as one added later, opens with its
// default.
type StoredFilters = Record<string, FilterValues[string] | null>

function key(dashboard: string) {
	return `insights:dashboard-filters:${session.user.email || 'Guest'}:${dashboard}`
}

function storedFilters(dashboard: string): StoredFilters {
	try {
		return JSON.parse(localStorage.getItem(key(dashboard)) || '{}')
	} catch {
		// a hand-edited or half-written entry must not break the page
		return {}
	}
}

export function readFilters(dashboard: string, defaults: FilterValues): FilterValues {
	const filters: FilterValues = {}
	Object.entries({ ...defaults, ...storedFilters(dashboard) }).forEach(([name, filter]) => {
		if (filter) filters[name] = filter
	})
	return filters
}

export function writeFilters(dashboard: string, filters: FilterValues, filterNames: string[]) {
	const stored: StoredFilters = {}
	filterNames.forEach((name) => (stored[name] = filters[name] ?? null))
	localStorage.setItem(key(dashboard), JSON.stringify(stored))
}
