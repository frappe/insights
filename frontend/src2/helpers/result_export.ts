import { toast } from 'frappe-ui'
import { ref } from 'vue'
import { saveExportedFile } from '../query/export_file'
import { __ } from '../translation'

/**
 * Save the rows a download endpoint writes.
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
				const saved = saveExportedFile(data, format, filename || defaultName() || 'data')
				toast.success(__('Export Successful'), {
					description: __(`File "{0}" exported successfully`, saved),
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
