import { toast } from 'frappe-ui'
import { ref } from 'vue'
import { __ } from '../translation'

const EXCEL_MIME = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

/**
 * Save the rows a download endpoint writes: CSV as text, Excel as base64.
 *
 * A cancelled download still runs on the server. Its answer is dropped when it
 * lands, so a later download is never saved under the earlier one's name.
 */
export function useResultExport(
	// eslint-disable-next-line no-unused-vars
	fetchFile: (format: string) => Promise<string | undefined>,
	defaultName: () => string,
) {
	const downloading = ref(false)
	let current: number | null = null

	function exportResults(format: string = 'csv', filename?: string) {
		const token = Date.now() + Math.random()
		current = token
		downloading.value = true
		return fetchFile(format)
			.then((data) => {
				if (current !== token) return
				if (!data) {
					toast.warning(__('Download Failed'), {
						description: __('No data found to download.'),
					})
					return
				}
				const excel = format === 'excel'
				const blob = excel
					? new Blob([Uint8Array.from(atob(data), (c) => c.charCodeAt(0))], {
							type: EXCEL_MIME,
					  })
					: new Blob([data], { type: 'text/csv' })
				const extension = excel ? 'xlsx' : 'csv'
				const finalFileName = `${filename || defaultName() || 'data'}.${extension}`
				const url = window.URL.createObjectURL(blob)
				const a = document.createElement('a')
				a.setAttribute('hidden', '')
				a.setAttribute('href', url)
				a.setAttribute('download', finalFileName)
				document.body.appendChild(a)
				a.click()
				document.body.removeChild(a)
				window.URL.revokeObjectURL(url)
				toast.success(__('Export Successful'), {
					description: __(`File "{0}" exported successfully`, finalFileName),
				})
			})
			.catch((error: any) => {
				if (current !== token) return
				toast.error(__('Download Failed'), {
					description: error?.message || __('Failed to download file'),
				})
			})
			.finally(() => {
				if (current !== token) return
				downloading.value = false
				current = null
			})
	}

	function cancelDownload() {
		current = null
		downloading.value = false
	}

	return { downloading, exportResults, cancelDownload }
}
