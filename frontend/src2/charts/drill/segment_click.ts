// A segment click, on its way from a chart to the drill menu.
//
// The adapter names a filler's click events and turns each payload into the
// point behind it. This turns that into one report a surface can act on, so the
// chart card and the drill dialog's own chart bind their clicks the same way —
// which is what makes drilling inside the dialog ride the path a chart already
// has, rather than a second one built for the dialog.

import type { QueryResultColumn } from '../../types/query.types'
import type { ChartFiller, DrillDownTarget } from '../adapter'

/** Where the reader clicked, in viewport coordinates. The menu opens there. */
export type ClickPoint = { x: number; y: number }

export type ChartSegmentClick = {
	target: DrillDownTarget
	point: ClickPoint
}

/**
 * The `v-on` map for a filler. A click that resolves to nothing drillable —
 * a donut's collapsed tail, a region the data does not carry — reports nothing.
 * A column the result does not carry is a mapping bug in the adapter, and it
 * says so rather than drilling into a column the server will reject.
 */
export function segmentClickEvents(
	filler: ChartFiller | undefined,
	columns: QueryResultColumn[],
	// eslint-disable-next-line no-unused-vars
	report: (target: DrillDownTarget) => void,
): Record<string, (payload: any) => void> {
	const resolvers = filler?.drillDown
	if (!resolvers) return {}

	return Object.fromEntries(
		Object.entries(resolvers).map(([event, resolve]) => [
			event,
			(payload: any) => {
				const target = resolve(payload)
				if (!target) return
				if (!columns.some((column) => column.name === target.column)) {
					console.warn(
						`[insights] Cannot drill down: no result column named "${target.column}".`,
					)
					return
				}
				report(target)
			},
		]),
	)
}
