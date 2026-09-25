import { call } from 'frappe-ui'
import session from '../session'

/** A module a workbook can ship in, as returned by `insights.api.workbooks.get_export_modules`. */
export type ExportModule = {
	module: string
	app: string
	/** The folder the module keeps its workbook files in. */
	folder: string
}

/**
 * Whether the workbook menu shows "Export to app…".
 *
 * Marking a workbook standard writes a file into an app's source. Only a site
 * in developer mode does that. A standard workbook already has its file.
 */
export function canExportToApp(workbook: { is_standard?: boolean | number }) {
	return Boolean(session.site.developer_mode) && !workbook.is_standard
}

export function getExportModules(): Promise<ExportModule[]> {
	return call('insights.api.workbooks.get_export_modules')
}

/** The names `mark_as_standard` accepts, which is what `cleanup_page_name` produces. */
export const WORKBOOK_NAME_PATTERN = /^[a-z0-9][a-z0-9-]*$/

/** The default name for a title, made the way `cleanup_page_name` makes it. */
export function toWorkbookName(title: string) {
	const name = (title || '')
		.toLowerCase()
		.replace(/[^a-z0-9-]+/g, '-')
		.replace(/-{2,}/g, '-')
		.replace(/^-+|-+$/g, '')
		.slice(0, 140)
	return WORKBOOK_NAME_PATTERN.test(name) ? name : ''
}

/** The file path the export writes, the same as `exported_file_path` with `frappe.scrub`. */
export function exportFilePath(module: ExportModule, name: string) {
	const folder = name.replace(/-/g, '_')
	return `${module.folder}/${folder}/${folder}.json`
}
