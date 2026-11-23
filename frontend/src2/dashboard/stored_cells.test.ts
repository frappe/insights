import { describe, expect, it } from 'vitest'
import type { WorkbookDashboardItem } from '../types/workbook.types'
import { withStoredCells } from './stored_cells'

const cell = (i: string, reading?: string, x = 0): WorkbookDashboardItem =>
	({
		type: 'chart',
		chart: 'kpis',
		...(reading ? { reading } : {}),
		layout: { i, x, y: 0, w: 4, h: 4 },
	}) as WorkbookDashboardItem

describe('a grid mid-edit when a chart’s readings change', () => {
	// @feature dashboard.number-cell-per-reading
	it('takes the stored cells of that chart and keeps the author’s place for each', () => {
		const local = [cell('a', 'revenue', 8), cell('b', 'orders', 12)]
		const stored = [cell('a', undefined, 0), cell('c', 'margin', 4)]

		expect(withStoredCells(local, stored, ['kpis'])).toEqual([
			cell('a', undefined, 8),
			cell('c', 'margin', 4),
		])
	})
})
