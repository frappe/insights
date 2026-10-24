// Reads workbook files on the client. `InsightsWorkbook.export` writes them for
// Copy JSON, Duplicate, the backup a delete leaves, and the file an app ships.
// The server's `is_workbook_file` decides whether a text is one.
//
// This module stands alone so that reading a file does not load the workbook
// store. That store pulls in the router and the whole Builder.

import { call } from 'frappe-ui'

/**
 * The workbook in a pasted text, if there is one.
 *
 * The server accepts two file shapes, so the check is left to it and not
 * repeated here. Only a JSON object is sent. Any other clipboard text stays in
 * the browser.
 */
export async function pastedWorkbook(text: string) {
	let json
	try {
		json = JSON.parse(text)
	} catch (e) {
		return undefined
	}
	if (!json || typeof json !== 'object' || Array.isArray(json)) return undefined
	const isWorkbook = await call('insights.api.workbooks.is_workbook_file', { workbook: json })
	return isWorkbook ? json : undefined
}
