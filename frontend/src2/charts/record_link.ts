// Which columns of a result name a desk document, and of which doctype, as the
// server traced it: keyed by result column name. Nothing here guesses a doctype
// from a column name — a miss draws no link rather than a link that lands on
// the wrong record.
export type RecordLinks = Record<string, string>

/** Where the desk opens that document, or nothing when the cell names none. */
export function recordUrl(doctype: string, value: unknown): string | undefined {
	if (value === null || value === undefined || value === '') return
	const route = doctype.toLowerCase().replace(/ /g, '-')
	return `/app/${route}/${encodeURIComponent(String(value))}`
}
