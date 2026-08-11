import { DonutChart } from 'frappe-ui/charts'
import type { DonutChartProps, DonutSliceEvent } from 'frappe-ui/charts'
import type { DonutChartConfig } from '../../types/chart.types'
import type { ChartAdapterInput, ChartFiller } from './types'

// The server groups a donut by its label column and orders the slices biggest
// first, so the result is already one row per slice, in the order the ring is
// read. Nothing here re-aggregates or re-sorts it.

export function adaptDonutChart(input: ChartAdapterInput): ChartFiller | undefined {
	const config = input.config as DonutChartConfig
	const category = config.label_column?.dimension_name || config.label_column?.column_name
	const value = config.value_column?.measure_name
	if (!category || !value) return

	const props: DonutChartProps = {
		title: input.title,
		data: input.result.rows,
		category,
		value,
	}
	// The tail is collapsed once, by the ring that draws it. `legend_position` has
	// no prop to move to: where the legend sits is the library's to decide.
	if (config.max_slices) props.maxSlices = config.max_slices
	if (config.show_inline_labels) props.showInlineLabels = true

	return {
		component: DonutChart,
		props,
		drillDown: {
			// The tail slice stands for every row under it, and a drill-down names
			// one row, so it drills into nothing rather than into the first of them.
			select: (event: DonutSliceEvent) =>
				event.rows.length === 1 ? { column: value, row: event.rows[0] } : undefined,
		},
	}
}
