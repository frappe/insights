import { BarChart, LineChart } from 'frappe-ui/charts'
import type {
	BarChartProps,
	ChartDatapointEvent,
	ChartMark,
	ChartValueAxisOptions,
	ChartXAxisOptions,
	ReferenceLine as PlotReferenceLine,
	SeriesStyle,
	TimeGrain,
} from 'frappe-ui/charts'
import type { Component } from 'vue'
import { FIELDTYPES, isCalendarDateType } from '../../helpers/constants'
import { getFormattedDate } from '../../query/helpers'
import type {
	MixedChartConfig,
	Series,
	SeriesLine,
	YAxisBar,
	YAxisLine,
} from '../../types/chart.types'
import type { Dimension } from '../../types/query.types'
import type { ChartAdapterInput, ChartFiller } from './types'

// Bar, Line and Row. One family, because they differ in two values: the mark an
// unmarked Series draws as, and whether the bars run across the plot.

export function adaptBarChart(input: ChartAdapterInput) {
	return adaptAxisChart(input, BarChart, 'bar')
}

export function adaptLineChart(input: ChartAdapterInput) {
	return adaptAxisChart(input, LineChart, 'line')
}

export function adaptRowChart(input: ChartAdapterInput) {
	return adaptAxisChart(input, BarChart, 'bar', true)
}

function adaptAxisChart(
	input: ChartAdapterInput,
	component: Component,
	mark: ChartMark,
	horizontal = false,
): ChartFiller | undefined {
	const config = input.config as MixedChartConfig
	const dimension = config.x_axis?.dimension
	const x = dimension?.dimension_name
	if (!x) return

	// A split renames the value columns after its own values, so the series a
	// chart draws are only knowable from the result. Without one they are the
	// Measures, under the names the summarize gave them. Either way the answer is
	// the same question asked of the result: which columns hold numbers.
	const columns = input.result.columns
		.filter((column) => FIELDTYPES.NUMBER.includes(column.type) && column.name !== x)
		.map((column) => column.name)
	if (!columns.length) return

	const y_axis = config.y_axis

	const seriesConfig: Record<string, SeriesStyle> = {}
	for (const column of columns) {
		const style = styleFor(config, seriesFor(config, column), mark)
		if (Object.keys(style).length) seriesConfig[column] = style
	}

	const hiddenSeries = columns.filter(
		(column) => seriesFor(config, column)?.hide_from_chart,
	)

	const props: BarChartProps = {
		title: input.title,
		data: input.result.rows,
		x,
		// Every value column, in the order the result carries them. Series colors
		// are handed out along this list, so the scale a Series is read on is said
		// in `seriesConfig` rather than by moving it.
		y: columns,
		xAxis: xAxisFor(dimension),
	}
	if (Object.keys(seriesConfig).length) props.seriesConfig = seriesConfig
	if (horizontal) props.horizontal = true

	const stacked = stackingFor(y_axis)
	if (stacked) props.stacked = stacked

	const yAxis = valueAxisFor(y_axis, Boolean(stacked === 'normalized'))
	if (Object.keys(yAxis).length) props.yAxis = yAxis

	const referenceLines = referenceLinesFor(y_axis)
	if (referenceLines.length) props.referenceLines = referenceLines

	return {
		component,
		props: hiddenSeries.length ? { ...props, hiddenSeries } : props,
		drillDown: {
			// The typed event carries the row it drew, so nothing maps an index
			// back onto the result.
			datapointClick: (event: ChartDatapointEvent) => ({
				column: event.seriesName,
				row: event.row,
			}),
		},
	}
}

/**
 * The Series that produced a value column. Without a split the column is the
 * Measure's own name. With one the column is named after a split value, so a
 * lone Measure owns every column, and several are told apart by their name
 * sitting inside the column's.
 */
function seriesFor(config: MixedChartConfig, column: string): Series | undefined {
	const series = (config.y_axis?.series || []).filter((s) => s.measure?.measure_name)
	if (!config.split_by?.dimension?.column_name) {
		return series.find((s) => s.measure.measure_name === column)
	}
	if (series.length === 1) return series[0]
	return series.find((s) => column.includes(s.measure.measure_name))
}

function styleFor(
	config: MixedChartConfig,
	series: Series | undefined,
	mark: ChartMark,
): SeriesStyle {
	const line = config.y_axis as YAxisLine
	const bar = config.y_axis as YAxisBar
	const style: SeriesStyle = {}

	const asked = series?.type || mark
	const area =
		asked === 'line' && ((series as SeriesLine)?.show_area ?? line.show_area)
	const type = area ? 'area' : asked
	if (type !== mark) style.type = type

	if (series?.color?.[0]) style.color = series.color[0]

	// A horizontal bar chart runs its value axis across the plot and draws only
	// one, so v2 reads every series against the primary there. Nothing here asks
	// which way the bars run: knowing it twice is how the two answers drift apart.
	if (series?.align === 'Right') style.axis = 'y2'

	const showDataLabels = series?.show_data_labels ?? config.y_axis?.show_data_labels
	if (showDataLabels) style.showDataLabels = true

	if (type === 'line' || type === 'area') {
		const smooth = (series as SeriesLine)?.smooth ?? line.smooth
		if (smooth) style.smooth = true
		const showDataPoints =
			(series as SeriesLine)?.show_data_points ?? line.show_data_points
		if (showDataPoints) style.showDataPoints = true
	}

	// Bars standing in front of each other rather than beside them is an
	// instruction to the renderer, not a reading of the data, so it goes through
	// the escape hatch rather than asking for a prop of its own.
	if (type === 'bar' && bar.overlap) style.echartOptions = { barGap: '-100%' }

	return style
}

/**
 * `normalize` reads every value as a share of its category, which only holds
 * once the shares are stacked into one column — so it carries the stack with it.
 * `overlap` puts the bars in front of each other, which a stack cannot do.
 */
function stackingFor(y_axis: MixedChartConfig['y_axis']): boolean | 'normalized' | undefined {
	const bar = y_axis as YAxisBar
	if (bar.normalize) return 'normalized'
	if (bar.stack && !bar.overlap) return true
	return undefined
}

function xAxisFor(dimension: Dimension): ChartXAxisOptions {
	if (FIELDTYPES.NUMBER.includes(dimension.data_type)) return { type: 'value' }
	if (!isCalendarDateType(dimension.data_type)) return { type: 'category' }

	const axis: ChartXAxisOptions = { type: 'time' }
	// The one grain a fiscal calendar adds and a plain one has no name for. It is
	// the reader's own year boundary, so Insights prints it.
	if (dimension.granularity === 'fiscal_year') {
		axis.format = (value: any) => getFormattedDate(value, 'fiscal_year')
	} else if (dimension.granularity) {
		axis.timeGrain = dimension.granularity as TimeGrain
	}
	return axis
}

function valueAxisFor(
	y_axis: MixedChartConfig['y_axis'],
	normalized: boolean,
): ChartValueAxisOptions {
	const axis: ChartValueAxisOptions = {}
	if (y_axis?.show_axis_label && y_axis.axis_label) axis.title = y_axis.axis_label
	// A normalized axis is pinned to the share it reads, 0 to 100.
	if (normalized) return axis
	if (y_axis?.min !== undefined) axis.min = y_axis.min
	if (y_axis?.max !== undefined) axis.max = y_axis.max
	return axis
}

function referenceLinesFor(y_axis: MixedChartConfig['y_axis']): PlotReferenceLine[] {
	return (y_axis?.reference_lines || [])
		.filter((line) => line.value !== undefined && line.value !== null && line.value !== '')
		.map((line) => {
			const onCategoryAxis = line.axis === 'x'
			const reference: PlotReferenceLine = {
				value: line.value as number | string,
				axis: onCategoryAxis ? 'x' : line.align === 'Right' ? 'y2' : 'y',
			}
			if (line.label) reference.label = line.label
			if (line.color) reference.color = line.color
			if (line.dashed) reference.dashed = true
			return reference
		})
}
