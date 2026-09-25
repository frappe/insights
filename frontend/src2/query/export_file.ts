// Every export endpoint returns only the file's text, for a Builder query or a
// reader's drilled rows alike. So one function turns that text into a download.

const EXCEL_TYPE = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

/**
 * Save exported text as a file, and return the file name.
 *
 * Excel arrives base64-encoded, because it is binary and the response is text.
 * CSV arrives as the file itself.
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
