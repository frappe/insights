import { BarChart, LineChart } from 'frappe-ui/charts'
import type {
	BarChartProps,
	ChartDatapointEvent,
	ChartMark,
	ChartTooltipColumn,
	ChartValueAxisOptions,
	ChartXAxisOptions,
	ReferenceLine as PlotReferenceLine,
	SeriesStyle,
	TimeGrain,
} from 'frappe-ui/charts'
import type { Component } from 'vue'
import { toNumber } from '../../helpers'
import { FIELDTYPES, isCalendarDateType } from '../../helpers/constants'
import { getFormattedDate } from '../../query/helpers'
import type {
	MixedChartConfig,
	ReferenceAggregate,
	ReferenceLine,
	Series,
	SeriesLine,
	YAxisBar,
	YAxisLine,
} from '../../types/chart.types'
import type { Dimension, QueryResultRow } from '../../types/query.types'
import { numberFormatter, type NumberFormatter } from '../number_format'
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

	// Measures that reach the tooltip and nothing else. They ride the same
	// summarize, so they arrive as value columns like any other — the config is
	// the only thing that says they are not series, which is why they are taken
	// out before the columns are read.
	const tooltipMeasures = tooltipMeasuresOf(config)

	// A split renames the value columns after its own values, so the series a
	// chart draws are only knowable from the result. Without one they are the
	// Measures, under the names the summarize gave them. Either way the answer is
	// the same question asked of the result: which columns hold numbers.
	const columns = input.result.columns
		.filter((column) => FIELDTYPES.NUMBER.includes(column.type) && column.name !== x)
		.map((column) => column.name)
		.filter((column) => !tooltipMeasures.includes(column))
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

	// One formatter per axis, not per series: v2 prints a value against the axis
	// it is read on, and an axis carries one scale. The first series drawn on it
	// says how that scale reads.
	const primary = numberFormatter(config, measureOn(config, 'Left'))
	props.yAxis = valueAxisFor(y_axis, Boolean(stacked === 'normalized'), primary)

	const right = measureOn(config, 'Right')
	if (right) props.y2Axis = { format: numberFormatter(config, right) }

	// A reference line reads any Measure the Chart carries, drawn or not: a target
	// on the tooltip is exactly the kind a rule is computed from.
	const referenceLines = referenceLinesFor(
		config,
		[...columns, ...tooltipMeasures],
		input.result.rows,
		primary,
	)
	if (referenceLines.length) props.referenceLines = referenceLines

	if (tooltipMeasures.length) {
		props.tooltipColumns = tooltipColumnsFor(config, tooltipMeasures)
	}

	return {
		component,
		props: hiddenSeries.length ? { ...props, hiddenSeries } : props,
		drillDown: {
			// The typed event carries the row it drew, so nothing maps an index
			// back onto the result.
			select: (event: ChartDatapointEvent) => ({
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

/**
 * The Measure a value column came from, drawn or not. A series is asked of
 * `seriesFor`, so a split — where the columns are named after the split's values
 * and one Measure owns several of them — answers the same way it does for a
 * mark. A tooltip Measure is never split, so its column is its own name.
 */
function measureNameFor(config: MixedChartConfig, column: string): string | undefined {
	const series = seriesFor(config, column)
	if (series) return series.measure?.measure_name
	return tooltipMeasuresOf(config).includes(column) ? column : undefined
}

/**
 * The Measures the tooltip carries, by the column name each one produced. Empty
 * under a split: a split fans every Measure out into one column per split value,
 * so there is no per-category column for one to arrive on, and the server
 * leaves them out of the pivot.
 */
function tooltipMeasuresOf(config: MixedChartConfig): string[] {
	if (config.split_by?.dimension?.column_name) return []
	const drawn = new Set(
		(config.y_axis?.series || [])
			.map((series) => series.measure?.measure_name)
			.filter(Boolean),
	)
	return (config.tooltip?.measures || [])
		.map((measure) => measure?.measure_name)
		.filter((name): name is string => Boolean(name) && !drawn.has(name))
}

/**
 * How each tooltip Measure prints. A tooltip value goes through the same number
 * format policy a series value does — the point of an extra is a number in
 * another unit, so it has to carry that unit. No label: a column takes the same
 * one the chart would give the Measure if it drew it.
 */
function tooltipColumnsFor(
	config: MixedChartConfig,
	names: string[],
): ChartTooltipColumn[] {
	const measures = config.tooltip?.measures || []
	return names.map((name) => {
		const format = numberFormatter(
			config,
			measures.find((m) => m?.measure_name === name),
		)
		return {
			name,
			// Only a number is formatted. A constant text attribute is reached by
			// picking a text column with `min`, and it prints as it stands.
			format: (value: number | string) =>
				typeof value === 'number' ? format(value) : String(value),
		}
	})
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

/**
 * The Measure whose format an axis takes: the first series sitting on it. A
 * chart drawing two Measures on one axis has already said they share a scale,
 * so it prints them the way it prints the first.
 */
function measureOn(config: MixedChartConfig, align: 'Left' | 'Right') {
	const series = (config.y_axis?.series || []).filter((s) => s.measure?.measure_name)
	const onAxis = series.filter((s) => (s.align === 'Right' ? 'Right' : 'Left') === align)
	return onAxis[0]?.measure
}

function valueAxisFor(
	y_axis: MixedChartConfig['y_axis'],
	normalized: boolean,
	format: NumberFormatter,
): ChartValueAxisOptions {
	const axis: ChartValueAxisOptions = { format }
	if (y_axis?.show_axis_label && y_axis.axis_label) axis.title = y_axis.axis_label
	// A normalized axis is pinned to the share it reads, 0 to 100.
	if (normalized) return axis
	if (y_axis?.min !== undefined) axis.min = y_axis.min
	if (y_axis?.max !== undefined) axis.max = y_axis.max
	return axis
}

/**
 * A reference line sits at a constant the author typed, or at an aggregate of a
 * Measure. v2 draws a rule at a value and computes nothing — it cannot, because
 * it hangs every rule on an empty host series so a legend toggle cannot take the
 * rule away with the data. So Insights reads the aggregate off the result, the
 * same way it derives the comparison delta, and hands over a plain value.
 */
function referenceLinesFor(
	config: MixedChartConfig,
	columns: string[],
	rows: QueryResultRow[],
	format: NumberFormatter,
): PlotReferenceLine[] {
	const lines: PlotReferenceLine[] = []
	for (const line of config.y_axis?.reference_lines || []) {
		const at = positionOf(line, config, columns, rows, format)
		if (!at) continue

		const reference: PlotReferenceLine = {
			value: at.value,
			axis: line.axis === 'x' ? 'x' : line.align === 'Right' ? 'y2' : 'y',
		}
		// A computed line labels itself, so a reader is never left with a rule and
		// no reason for it. What the author typed wins.
		const label = line.label || at.label
		if (label) reference.label = label
		if (line.color) reference.color = line.color
		if (line.dashed) reference.dashed = true
		lines.push(reference)
	}
	return lines
}

/** Where a line sits, and the label it names itself. Undrawable lines answer nothing. */
type ReferencePosition = { value: number | string; label?: string }

/**
 * The kind of a line is read, not stored: an `aggregate` and a Measure make it
 * computed, and anything else is a constant. So a line saved before computed
 * lines existed carries a `value` alone and still reads as one.
 */
function positionOf(
	line: ReferenceLine,
	config: MixedChartConfig,
	columns: string[],
	rows: QueryResultRow[],
	format: NumberFormatter,
): ReferencePosition | undefined {
	if (line.aggregate) return aggregatePositionOf(line, config, columns, rows, format)
	if (line.value === undefined || line.value === null || line.value === '') return
	return { value: line.value as number | string }
}

function aggregatePositionOf(
	line: ReferenceLine,
	config: MixedChartConfig,
	columns: string[],
	rows: QueryResultRow[],
	format: NumberFormatter,
): ReferencePosition | undefined {
	const aggregate = line.aggregate
	const measure = line.measure_name
	if (!aggregate || !measure) return

	const sources = columns.filter((column) => measureNameFor(config, column) === measure)

	// Every number the chart draws for those columns. Not the category totals: a
	// stack is the one picture they read better on, and one rule that holds
	// everywhere beats two that are each right once.
	const values = sources
		.flatMap((column) => rows.map((row) => toNumber(row[column])))
		.filter((value): value is number => value !== null)
	// A Measure the query no longer returns, or one with nothing numeric in it,
	// leaves the line with nowhere to sit. Drawing it at zero would be a lie.
	if (!values.length) return

	const value = aggregateOf(aggregate, values)
	// The label prints on the plot, beside the ticks the same formatter drew.
	return { value, label: `${AGGREGATE_LABELS[aggregate]} ${measure}: ${format(value)}` }
}

/** What a computed line's own label leads with. Short: it is printed on the plot. */
const AGGREGATE_LABELS: Record<ReferenceAggregate, string> = {
	average: 'Avg',
	median: 'Median',
	min: 'Min',
	max: 'Max',
	sum: 'Sum',
}

function aggregateOf(aggregate: ReferenceAggregate, values: number[]): number {
	if (aggregate === 'min') return Math.min(...values)
	if (aggregate === 'max') return Math.max(...values)

	if (aggregate === 'median') {
		const sorted = [...values].sort((a, b) => a - b)
		const middle = Math.floor(sorted.length / 2)
		// An even count has no middle value, so the two either side of it average.
		return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2
	}

	const total = values.reduce((sum, value) => sum + value, 0)
	return aggregate === 'sum' ? total : total / values.length
}
