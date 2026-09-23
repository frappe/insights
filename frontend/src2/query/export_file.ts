// The one place the browser is made to save a file.
//
// Every export answers with the text of a file and nothing else — the builder's
// query, a reader's drilled rows — so how that text becomes a download is one
// implementation, not one per caller.

const EXCEL_TYPE = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

/**
 * Save exported text as a file, and answer with the name it was saved under.
 *
 * Excel arrives base64-encoded because it is bytes and the response is text.
 * Everything else is the file already.
 */
export function saveExportedFile(data: string, format: string, filename: string): string {
	const excel = format === 'excel'
	const blob = excel
		? new Blob([Uint8Array.from(atob(data), (c) => c.charCodeAt(0))], { type: EXCEL_TYPE })
		: new Blob([data], { type: 'text/csv' })
	const saved = `${filename}.${excel ? 'xlsx' : 'csv'}`

	const url = window.URL.createObjectURL(blob)
	const anchor = document.createElement('a')
	anchor.setAttribute('hidden', '')
	anchor.setAttribute('href', url)
	anchor.setAttribute('download', saved)
	document.body.appendChild(anchor)
	anchor.click()
	document.body.removeChild(anchor)
	window.URL.revokeObjectURL(url)

	return saved
}
