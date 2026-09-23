import { call } from 'frappe-ui'
import session from '../session'

/** A module a workbook can be shipped in, as `insights.api.workbooks.get_export_modules` answers. */
export type ExportModule = {
	module: string
	app: string
	/** The folder the module keeps its workbook files in. */
	folder: string
}

/**
 * Whether the workbook menu offers "Export to app…".
 *
 * Marking a workbook standard writes a file into an app's source, which only a
 * developer-mode bench does, and a workbook that is standard already has its
 * file — the menu has nothing left to offer it.
 */
export function canExportToApp(workbook: { is_standard?: boolean | number }) {
	return Boolean(session.site.developer_mode) && !workbook.is_standard
}

export function getExportModules(): Promise<ExportModule[]> {
	return call('insights.api.workbooks.get_export_modules')
}

/** The names `mark_as_standard` accepts: what `cleanup_page_name` leaves behind. */
export const WORKBOOK_NAME_PATTERN = /^[a-z0-9][a-z0-9-]*$/

/** The name a title defaults to, as `cleanup_page_name` makes it. */
export function toWorkbookName(title: string) {
	const name = (title || '')
		.toLowerCase()
		.replace(/[^a-z0-9-]+/g, '-')
		.replace(/-{2,}/g, '-')
		.replace(/^-+|-+$/g, '')
		.slice(0, 140)
	return WORKBOOK_NAME_PATTERN.test(name) ? name : ''
}

/** The file the export writes, the way `exported_file_path` names it under `frappe.scrub`. */
export function exportFilePath(module: ExportModule, name: string) {
	const folder = name.replace(/-/g, '_')
	return `${module.folder}/${folder}/${folder}.json`
}
