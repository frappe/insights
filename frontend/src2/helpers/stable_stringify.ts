/**
 * JSON with every object's keys in one order, so two values that differ only in
 * key order serialize alike.
 *
 * The server sorts the keys of every JSON field it stores (`frappe.as_json`
 * passes `sort_keys`), so a document that has been saved comes back holding the
 * same content in a different order. Compare the plain `JSON.stringify` of the
 * two and the value reads as new.
 */
export function stableStringify(value: any): string {
	return JSON.stringify(withSortedKeys(value))
}

function withSortedKeys(value: any): any {
	if (Array.isArray(value)) return value.map(withSortedKeys)
	if (value && typeof value === 'object') {
		const sorted: Record<string, any> = {}
		for (const key of Object.keys(value).sort()) {
			sorted[key] = withSortedKeys(value[key])
		}
		return sorted
	}
	return value
}
