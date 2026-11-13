import type { WorkbookDashboardItem } from '../types/workbook.types'

/**
 * The author's grid with the stored cells of `charts`: the server added or
 * dropped some, and changed the reading of others (`follow_readings`). Each
 * cell both hold takes the stored cell and keeps the author's place.
 */
export function withStoredCells(
	local: WorkbookDashboardItem[],
	stored: WorkbookDashboardItem[],
	charts: string[],
): WorkbookDashboardItem[] {
	const ofCharts = (item: WorkbookDashboardItem) =>
		item.type === 'chart' && charts.includes(item.chart)
	const storedCells = new Map(stored.filter(ofCharts).map((item) => [item.layout.i, item]))
	const localIds = new Set(local.filter(ofCharts).map((item) => item.layout.i))
	return [
		...local.flatMap((item) => {
			if (!ofCharts(item)) return [item]
			const kept = storedCells.get(item.layout.i)
			return kept ? [{ ...kept, layout: item.layout, layouts: item.layouts }] : []
		}),
		...stored.filter((item) => ofCharts(item) && !localIds.has(item.layout.i)),
	]
}
