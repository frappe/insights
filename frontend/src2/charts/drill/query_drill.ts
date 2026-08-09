// The query builder's own result, drilled.
//
// A chart card hands the drill a subject off its read store. A query has no such
// store — it has the pipeline it is editing — so the subject is assembled here:
// the aggregating step read as a Chart, so a cell click pins the same columns it
// would on a Table card, and the authoring door told the whole pipeline, so the
// server still decides where to cut it.
//
// The candidates are the one thing that cannot ride along. A chart's arrive with
// its rows; a query fetches its rows through its own document, so there is no
// response for them to arrive on and they are asked for on their own. That is
// one round trip between the double-click and the menu, on this surface only.

import type { Query } from '../../query/query'
import { fetchAuthoringDrillData, fetchAuthoringDrillDimensions } from './drill_api'
import { queryResultChart, type DrillSubject } from './drill_stack'

/** Undefined when nothing in the pipeline aggregates, which has nothing behind it. */
export async function queryDrillSubject(query: Query): Promise<DrillSubject | undefined> {
	const operations = query.currentOperations
	const chart = queryResultChart(operations)
	if (!chart) return

	const subject = { query: query.doc.name, operations }
	return {
		chart,
		title: query.doc.title,
		dimensions: await fetchAuthoringDrillDimensions(subject),
		fetch: (levels) => fetchAuthoringDrillData(subject, levels),
	}
}
