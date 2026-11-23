import { __ } from '../translation'

export type AppliedUserPermission = { doctype: string; documents: string[] }

// How many documents to name per doctype before the rest are only counted.
// Thirty territory names tell the reader nothing, and the tooltip would be
// taller than the card.
const NAMED_DOCUMENTS = 5

/**
 * What a card says when the reader's own permissions narrowed its rows.
 *
 * "User Permissions" is Frappe's name for the record, so a reader who wants to
 * know why a number is low has a term to look up, in the desk or with whoever
 * granted it. A team's Table Restriction and a column hidden on some rows name
 * no documents, so `narrowed` only says that the reader's permissions did it.
 *
 * One message in two forms: `lines` for the tooltip, which has room for one line
 * per doctype, and `sentence` for the mark's label, which is read in one go.
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
