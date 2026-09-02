import { HeatmapChart } from 'frappe-ui/charts'
import type { HeatmapCellEvent, HeatmapChartProps } from 'frappe-ui/charts'
import { isCalendarDateType } from '../../helpers/constants'
import { getAxisDate } from '../../query/helpers'
import type { Dimension } from '../../types/query.types'
import type { HeatmapChartConfig } from '../../types/chart.types'
import type { ChartAdapterInput, ChartFiller } from './types'

// The server groups a heatmap by both of its dimensions, so the result is
// already one row per cell. A pair with no rows returns no row, and the grid
// leaves that cell empty rather than coloring it zero.

export function adaptHeatmapChart(input: ChartAdapterInput): ChartFiller | undefined {
	const config = input.config as HeatmapChartConfig
	const x = config.x_column?.dimension_name || config.x_column?.column_name
	const y = config.y_column?.dimension_name || config.y_column?.column_name
	const value = config.value_column?.measure_name
	if (!x || !y || !value) return

	const props: HeatmapChartProps = {
		title: input.title,
		data: input.result.rows,
		x,
		y,
		value,
	}
	// Both cuts of a grid are category axes, so neither gets the time axis that
	// prints an axis chart's dates. The grain the Dimension was grouped by is
	// what says how to print them, the same grain `xAxisFor` reads.
	const xFormat = dateFormatFor(config.x_column)
	const yFormat = dateFormatFor(config.y_column)
	if (xFormat) props.xAxis = { format: xFormat }
	if (yFormat) props.yAxis = { format: yFormat }

	if (config.show_values) props.showValues = true
	if (config.palette) props.palette = config.palette
	if (typeof config.min === 'number') props.min = config.min
	if (typeof config.max === 'number') props.max = config.max

	return {
		component: HeatmapChart,
		props,
		drillDown: {
			select: (event: HeatmapCellEvent) => ({ column: value, row: event.row }),
		},
	}
}

/**
 * How a cut prints, when it is a date one. A plain category prints itself.
 *
 * Abbreviated, because these are axis ticks: a grid draws a label per column,
 * and the columns are as narrow as the cells. The axis charts get the same
 * reading from `timeGrain`, which a category axis has nowhere to put.
 */
function dateFormatFor(dimension?: Dimension) {
	if (!dimension?.granularity || !isCalendarDateType(dimension.data_type)) return
	const granularity = dimension.granularity
	return (value: any) => getAxisDate(value, granularity)
}
