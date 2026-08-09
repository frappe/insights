// A breakdown level as a Chart.
//
// The level is the clicked Measure read across the chosen Dimension, and that is
// a Row chart — the one the dashboard already draws. So the level builds a Row
// chart's config and hands it to the same adapter every card goes through. There
// is no bar list of the drill's own: if the reading ever wants denser bars, the
// Row chart gets them, and every dashboard gets them with it.
//
// The ranking is not here either. A breakdown level arrives ordered by the
// Measure, largest first — the server ordered it, which is also what makes the
// one page it returns the top of the list rather than an arbitrary slice.

import type { ChartConfig } from '../../types/chart.types'
import type { QueryResultColumn } from '../../types/query.types'
import type { DrillChart } from './drill_stack'

/** The Chart a breakdown level draws itself as. */
export function breakdownChart(
	dimension: string,
	measure: string,
	columns: QueryResultColumn[],
): DrillChart {
	const type = columns.find((column) => column.name === dimension)?.type || 'String'

	return {
		chart_type: 'Row',
		config: {
			x_axis: {
				dimension: {
					dimension_name: dimension,
					column_name: dimension,
					data_type: type as any,
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
				// the ranking is the whole point of the level, so every bar is read
				show_data_labels: true,
			},
			order_by: [],
			limit: 100,
		} as unknown as ChartConfig,
	}
}

