// What a workbook file is, as the client reads one. `InsightsWorkbook.export`
// writes it — for Copy JSON, for Duplicate, for the backup a delete leaves
// behind and for the file an app ships — and the server's `is_workbook_file` is
// what says a text is one.
//
// It stands alone so that reading a file costs none of the workbook store: that
// reaches the router and the whole builder aggregate.

import { call } from 'frappe-ui'

/**
 * The workbook a pasted text holds, if it holds one.
 *
 * The server reads two shapes of file, and it is asked rather than restated
 * here. Only a JSON object is sent: whatever else is on the clipboard stays in
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
