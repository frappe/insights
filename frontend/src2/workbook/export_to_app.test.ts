import { afterEach, describe, expect, it } from 'vitest'
import session from '../session'
import {
	ExportModule,
	WORKBOOK_NAME_PATTERN,
	canExportToApp,
	exportFilePath,
	toWorkbookName,
} from './export_to_app'

afterEach(() => {
	session.site.developer_mode = false
})

describe('the menu item', () => {
	// @feature standard.export-to-app
	it('is shown to an author on a developer-mode bench', () => {
		session.site.developer_mode = true
		expect(canExportToApp({ is_standard: false })).toBe(true)
	})

	// @feature standard.export-to-app
	it('is withheld on a bench that cannot write to an app', () => {
		expect(canExportToApp({ is_standard: false })).toBe(false)
	})

	// @feature standard.export-to-app
	it('is withheld from a workbook an app already ships', () => {
		session.site.developer_mode = true
		expect(canExportToApp({ is_standard: true })).toBe(false)
	})
})

describe('the name a workbook ships under', () => {
	// @feature standard.export-to-app
	it('defaults to the title, as the server slugs it', () => {
		expect(toWorkbookName('Selling Board')).toBe('selling-board')
		expect(toWorkbookName('Sales & Revenue, 2026')).toBe('sales-revenue-2026')
		expect(toWorkbookName('  Stock  ')).toBe('stock')
	})

	// @feature standard.export-to-app
	it('is empty when the title leaves nothing to name it with', () => {
		expect(toWorkbookName('')).toBe('')
		expect(toWorkbookName('—')).toBe('')
	})

	// @feature standard.export-to-app
	it('is refused when it is not what the server would have written', () => {
		expect(WORKBOOK_NAME_PATTERN.test('selling-board')).toBe(true)
		expect(WORKBOOK_NAME_PATTERN.test('Selling Board')).toBe(false)
		expect(WORKBOOK_NAME_PATTERN.test('-selling')).toBe(false)
		expect(WORKBOOK_NAME_PATTERN.test('selling/board')).toBe(false)
	})
})

describe('the file the export writes', () => {
	const selling: ExportModule = {
		module: 'Selling',
		app: 'erpnext',
		folder: '/bench/apps/erpnext/erpnext/selling/insights_workbook',
	}

	// @feature standard.export-to-app
	it('is named after the workbook, scrubbed the way the module folder is', () => {
		expect(exportFilePath(selling, 'selling-board')).toBe(
			'/bench/apps/erpnext/erpnext/selling/insights_workbook/selling_board/selling_board.json',
		)
	})
})
