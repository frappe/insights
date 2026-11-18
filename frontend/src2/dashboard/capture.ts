// The server draws a dashboard as an image (`insights.api.view.get_dashboard_image`)
// by opening its shared page in a browser with `?capture`. The page then lays out
// at its full height, opens on the filters the caller sent, and marks the document
// once every card has drawn, so the capture waits for that and not a fixed time.

import type { LocationQuery } from 'vue-router'
import type { FilterValues } from '../types/workbook.types'
import type { DashboardView } from './view'

export const DRAWN_ATTRIBUTE = 'data-dashboard-drawn'

// frappe-ui's entry animation of a chart, and its count-up of a number, with a margin
const ENTRY_ANIMATION_MS = 800

export function isCapture(query: LocationQuery) {
	return query.capture !== undefined
}

export function captureFilters(query: LocationQuery): FilterValues | undefined {
	return typeof query.filters === 'string' ? JSON.parse(query.filters) : undefined
}

/** Whether every card has its answer: rows, an empty result, a refusal or a failure. */
export function cardsSettled(dashboard: DashboardView) {
	if (dashboard.loading) return false
	if (dashboard.notFound || dashboard.noAccess || dashboard.failed) return true
	return dashboard.items.every(
		(item) => item.type !== 'chart' || dashboard.chartView(item.chart!)?.executing === false,
	)
}

/** Marks the document drawn once the charts that just got their rows have animated in. */
export function markDrawn() {
	requestAnimationFrame(() =>
		setTimeout(
			() => document.documentElement.setAttribute(DRAWN_ATTRIBUTE, ''),
			ENTRY_ANIMATION_MS,
		),
	)
}
