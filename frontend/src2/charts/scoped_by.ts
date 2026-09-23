import { __ } from '../translation'

export type AppliedUserPermission = { doctype: string; documents: string[] }

// The most documents one doctype names before the rest are counted: a reader
// with access to thirty territories learns nothing from thirty names, and the
// bubble would be taller than the card it hangs off.
const NAMED_DOCUMENTS = 5

/**
 * What a card whose rows the reader's own permissions narrowed says.
 *
 * "User Permissions" is frappe's own name for the record, so a reader who wants
 * to know why a number is short has a term to look up — in the desk, or from
 * whoever granted it. A team's Table Restriction and a column blanked on some
 * rows name nothing, so `narrowed` says only that their permissions did it.
 *
 * One fact in two shapes: `lines` for the bubble, which has room for a line per
 * doctype, and `sentence` for the mark's label, which is read in one go.
 */
export function scopeText(applied?: AppliedUserPermission[], narrowed = false) {
	const narrowedLine = __('Narrowed by your permissions')
	if (!applied?.length) {
		return narrowed ? { heading: narrowedLine, lines: [], sentence: narrowedLine } : null
	}

	const heading = __('Filtered by your User Permissions')
	const lines = [...applied]
		.sort((a, b) => a.doctype.localeCompare(b.doctype))
		.map((one) => `${one.doctype}: ${documentsNamed(one.documents)}`)
	if (narrowed) lines.push(narrowedLine)

	return { heading, lines, sentence: `${heading}: ${lines.join('; ')}` }
}

function documentsNamed(documents: string[]) {
	const named = documents.slice(0, NAMED_DOCUMENTS).join(', ')
	const rest = documents.length - NAMED_DOCUMENTS
	return rest > 0 ? `${named} ${__('and {0} more', String(rest))}` : named
}
