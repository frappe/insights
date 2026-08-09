// A breakdown level as a Chart.
//
// The level is the clicked Measure read across the chosen Dimension, and that is
// one of the two charts the dashboard already draws. So the level builds their
// config and hands it to the same adapter every card goes through. There is no
// bar list of the drill's own: if the reading ever wants denser bars, the Row
// chart gets them, and every dashboard gets them with it.
//
// Which of the two is the answer's own reading of the Dimension. A Dimension
// with an order of its own — a date — came back in that order, cut to the most
// recent stretch, and a line is how a stretch of time is read. Anything else
// came back ranked by the Measure, largest first, which is a Row chart. The flag
// is the server's; nothing here looks at a column's type to decide, because the
// order the rows arrived in and the shape drawn from them have to agree.

import type { ChartConfig } from '../../types/chart.types'
import type { DrillChart, DrillLevelData } from './drill_stack'

/** What a breakdown level draws itself from: the answer, less its rows. */
export type BreakdownAnswer = Pick<DrillLevelData, 'columns' | 'ordered' | 'granularity'>

/** The Chart a breakdown level draws itself as. */
export function breakdownChart(
	dimension: string,
	measure: string,
	answer: BreakdownAnswer,
): DrillChart {
	const type = answer.columns.find((column) => column.name === dimension)?.type || 'String'
	const ordered = Boolean(answer.ordered)

	return {
		chart_type: ordered ? 'Line' : 'Row',
		config: {
			x_axis: {
				dimension: {
					dimension_name: dimension,
					column_name: dimension,
					data_type: type as any,
					// what the buckets on the axis stand for. It prints them, and it is
					// also what a click inside the level reads its own crumb at.
					granularity: answer.granularity || undefined,
				},
			},
			y_axis: {
				series: [
					{
						measure: {
							measure_name: measure,
							column_name: measure,
							data_type: 'Decimal',
							aggregation: 'sum',
						},
					},
				],
				// the ranking is the whole point of a ranked level, so every bar is
				// read. A stretch of time is read as a shape, and a label on every
				// point of it buries the shape.
				show_data_labels: !ordered,
			},
			order_by: [],
			limit: 100,
		} as unknown as ChartConfig,
	}
}
