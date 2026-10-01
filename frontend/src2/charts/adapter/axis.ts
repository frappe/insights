import { __, translatedTable } from '../../translation'
import { BarChart, LineChart } from 'frappe-ui/charts'
import type {
	BarChartProps,
	ChartDatapointEvent,
	ChartMark,
	ChartTooltipColumn,
	ChartValueAxisOptions,
	ChartXAxisOptions,
	ChartTokens,
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
import { hasBarsOnBothAxes } from '../helpers'
import { numberFormatter, type NumberFormatter } from '../number_format'
import type { ChartAdapterInput, ChartFiller } from './types'

// Bar, Line and Row. One family, because they differ in two values: the mark an
// unmarked Series plots as, and whether the bars run across the plot.

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

	// Measures that reach the tooltip and nothing else. The same summarize returns
	// them, so they arrive as value columns like any other — the config is
	// the only thing that says they are not series, which is why they are taken
	// out before the columns are read.
	const tooltipMeasures = tooltipMeasuresOf(config)

	// A split renames the value columns after its own values, so the series a
	// chart plots are only knowable from the result. Without one they are the
	// Measures, under the names the summarize gave them. Either way the answer is
	// the same question asked of the result: which columns hold numbers.
	const columns = input.result.columns
		.filter((column) => FIELDTYPES.NUMBER.includes(column.type) && column.name !== x)
		.map((column) => column.name)
		.filter((column) => !tooltipMeasures.includes(column))
	if (!columns.length) return

	const y_axis = config.y_axis
	const barsOnBothAxes = hasBarsOnBothAxes(y_axis?.series, mark, horizontal)
	const overlap = Boolean((y_axis as YAxisBar | undefined)?.overlap) && !barsOnBothAxes

	const seriesByColumn = new Map(columns.map((column) => [column, seriesFor(config, column)]))
	// A split hands one Series several columns, and the color the form wrote is
	// one color: painting it on each of them plots the split in a single shade.
	// Every other thing a Series says — the mark, the area, the labels — is true
	// of all its columns, so only the color asks how many it owns.
	const columnsOwned = new Map<Series, number>()
	for (const series of seriesByColumn.values()) {
		if (series) columnsOwned.set(series, (columnsOwned.get(series) || 0) + 1)
	}

	const styles = new Map(
		columns.map((column) => {
			const series = seriesByColumn.get(column)
			const owns = series ? columnsOwned.get(series) === 1 : false
			return [column, styleFor(config, series, mark, owns, overlap, horizontal)]
		}),
	)

	// A horizontal bar chart runs its value axis across the plot and plots only
	// one, so v2 reads every series against the primary there. Nothing here asks
	// which way the bars run: knowing it twice is how the two answers drift apart.
	const onRight = (column: string) => seriesByColumn.get(column)?.align === 'Right'
	const right = columns.filter(onRight)

	const props: BarChartProps = {
		title: input.title,
		subtitle: input.description,
		data: input.result.rows,
		x,
		y: columns.filter((column) => !onRight(column)),
		xAxis: xAxisFor(dimension),
	}
	if (right.length) props.y2 = right
	if (horizontal) props.horizontal = true

	const stacking = stackingFor(y_axis, barsOnBothAxes)
	if (stacking) props.stacked = stacking

	// One formatter per axis, not per series: v2 prints a value against the axis
	// it is read on, and an axis has one scale. The first series plotted on it
	// says how that scale reads.
	const primary = numberFormatter(config, measureOn(config, 'Left'), input.result.rows)
	props.yAxis = valueAxisFor(y_axis, stacking === 'normalized', primary)

	const rightMeasure = measureOn(config, 'Right')
	const secondary = rightMeasure
		? numberFormatter(config, rightMeasure, input.result.rows)
		: undefined
	if (secondary) props.y2Axis = { format: secondary }

	// The form asks the same question of each Series, so a line is drawn exactly
	// where a toggle offers one.
	const trends = trendLinesFor(
		config,
		columns.filter((column) => {
			const series = seriesByColumn.get(column)
			return series?.show_trend_line && takesTrendLine(config, series, mark, horizontal)
		}),
		input.result.rows,
		horizontal,
		// v2 reads a horizontal chart's every series on its one value axis
		(column) => (onRight(column) && !horizontal ? props.y2Axis : props.yAxis),
		input.tokens,
	)

	const seriesConfig: Record<string, SeriesStyle> = {}
	for (const [column, style] of styles) {
		const trend = trends.get(column)
		if (trend) style.echartOptions = { ...style.echartOptions, markLine: trend }
		if (Object.keys(style).length) seriesConfig[column] = style
	}

	if (Object.keys(seriesConfig).length) props.seriesConfig = seriesConfig

	// A reference line reads any Measure the Chart includes, plotted or not: a rule
	// often computes from a tooltip target.
	const referenceLines = referenceLinesFor(
		config,
		[...columns, ...tooltipMeasures],
		input.result.rows,
		primary,
		secondary,
	)
	if (referenceLines.length) props.referenceLines = referenceLines

	if (tooltipMeasures.length) {
		props.tooltipColumns = tooltipColumnsFor(config, tooltipMeasures, input.result.rows)
	}

	return {
		component,
		props,
		drillDown: {
			// The typed event includes the row it plotted, so nothing maps an index
			// back onto the result.
			select: (event: ChartDatapointEvent) => ({
				column: event.name,
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
	// the split's values trail the Measure's name, so the head of the column is
	// the Measure: `revenue` does not own `net_revenue___North`
	const head = column.split('___').slice(0, -1).join('___')
	return series.find((s) => s.measure.measure_name === head)
}

/**
 * The Measure a value column came from, plotted or not. A series is asked of
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
 * The Measures the tooltip includes, by the column name each one produced. Empty
 * under a split: a split turns every Measure into one column per split value,
 * so there is no per-category column for one to arrive on, and the server
 * leaves them out of the pivot.
 */
function tooltipMeasuresOf(config: MixedChartConfig): string[] {
	if (config.split_by?.dimension?.column_name) return []
	const plotted = new Set(
		(config.y_axis?.series || []).map((series) => series.measure?.measure_name).filter(Boolean),
	)
	return (config.tooltip?.measures || [])
		.map((measure) => measure?.measure_name)
		.filter((name): name is string => Boolean(name) && !plotted.has(name))
}

/**
 * How each tooltip Measure prints. A tooltip value goes through the same number
 * format policy a series value does — the point of an extra is a number in
 * another unit, so it has to keep that unit. No label: a column takes the same
 * one the chart would give the Measure if it plotted it.
 */
function tooltipColumnsFor(
	config: MixedChartConfig,
	names: string[],
	rows: QueryResultRow[],
): ChartTooltipColumn[] {
	const measures = config.tooltip?.measures || []
	return names.map((name) => {
		const format = numberFormatter(
			config,
			measures.find((m) => m?.measure_name === name),
			rows,
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
	ownsOneColumn: boolean,
	overlap: boolean,
	horizontal: boolean,
): SeriesStyle {
	// the slots the normalizer writes, read the way every other line here reads
	// them: an entry point that bypasses it must not blank the card
	const line = (config.y_axis || {}) as YAxisLine
	const style: SeriesStyle = {}

	const type = markOf(config, series, mark, horizontal)
	if (type !== mark) style.type = type

	if (ownsOneColumn && series?.color?.[0]) style.color = series.color[0]

	const showDataLabels = series?.show_data_labels ?? config.y_axis?.show_data_labels
	if (showDataLabels) style.showDataLabels = true

	if (type === 'line' || type === 'area') {
		const smooth = (series as SeriesLine)?.smooth ?? line.smooth
		if (smooth) style.smooth = true
		const showDataPoints = (series as SeriesLine)?.show_data_points ?? line.show_data_points
		if (showDataPoints) style.showDataPoints = true
	}

	// Bars standing in front of each other rather than beside them is an
	// instruction to the renderer, not a reading of the data, so it goes through
	// `echartOptions` rather than asking for a prop of its own.
	if (type === 'bar' && overlap) style.echartOptions = { barGap: '-100%' }

	return style
}

/**
 * `normalize` reads every value as a share of its category, which only holds
 * once the shares are stacked into one column — so it brings the stack with it.
 * `overlap` puts the bars in front of each other, which a stack cannot do.
 * Bars on both axes are two scales, and no column sums them.
 */
function stackingFor(
	y_axis: MixedChartConfig['y_axis'],
	barsOnBothAxes: boolean,
): boolean | 'normalized' | undefined {
	if (barsOnBothAxes) return undefined
	const bar = (y_axis || {}) as YAxisBar
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
 * chart plotting two Measures on one axis has already said they share a scale,
 * so it prints them the way it prints the first.
 *
 * A chart that put every series on the right has none on the left, and the left
 * is the axis the ticks are still plotted against. It prints the way the chart's
 * first Measure prints, rather than unformatted.
 */
function measureOn(config: MixedChartConfig, align: 'Left' | 'Right') {
	const series = (config.y_axis?.series || []).filter((s) => s.measure?.measure_name)
	const onAxis = series.filter((s) => (s.align === 'Right' ? 'Right' : 'Left') === align)
	if (onAxis.length) return onAxis[0].measure
	return align === 'Left' ? series[0]?.measure : undefined
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
	if (typeof y_axis?.min === 'number') axis.min = y_axis.min
	if (typeof y_axis?.max === 'number') axis.max = y_axis.max
	return axis
}

/**
 * A reference line sits at a constant the author typed, or at an aggregate of a
 * Measure. v2 plots a rule at a value and computes nothing — it cannot, because
 * it hangs every rule on an empty host series so a legend toggle cannot take the
 * rule away with the data. So Insights reads the aggregate off the result, the
 * same way it derives the comparison delta, and hands over a plain value.
 */
function referenceLinesFor(
	config: MixedChartConfig,
	columns: string[],
	rows: QueryResultRow[],
	format: NumberFormatter,
	rightFormat?: NumberFormatter,
): PlotReferenceLine[] {
	const lines: PlotReferenceLine[] = []
	for (const line of config.y_axis?.reference_lines || []) {
		// A line labels itself in the scale it is plotted against, so a rule on the
		// right axis reads as that axis's ticks do.
		const on = line.align === 'Right' && rightFormat ? rightFormat : format
		const at = positionOf(line, config, columns, rows, on)
		if (!at) continue

		const reference: PlotReferenceLine = {
			value: at.value,
			axis: line.axis === 'x' ? 'x' : line.align === 'Right' ? 'y2' : 'y',
		}
		// A computed line labels itself, so a reader is never left with a rule and
		// no reason for it. What the author typed wins.
		const label = line.label || at.label
		if (label) reference.label = label
		if (line.label_placement) reference.labelPlacement = line.label_placement
		if (line.color) reference.color = line.color
		if (line.dashed) reference.dashed = true
		lines.push(reference)
	}
	return lines
}

/** Where a line sits, and the label it names itself. Lines that cannot be plotted answer nothing. */
type ReferencePosition = { value: number | string; label?: string }

/**
 * The kind of a line is read, not stored: an `aggregate` and a Measure make it
 * computed, and anything else is a constant. So a line saved before computed
 * lines existed has a `value` alone and still reads as one.
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

	// Every number the chart plots for those columns. Not the category totals: a
	// stack is the one chart they read better on, and one rule that holds
	// everywhere beats two that are each right once.
	const values = sources
		.flatMap((column) => rows.map((row) => toNumber(row[column])))
		.filter((value): value is number => value !== null)
	// A Measure the query no longer returns, or one with nothing numeric in it,
	// leaves the line with nowhere to sit.
	if (!values.length) return

	const value = aggregateOf(aggregate, values)
	// The label prints on the plot, beside the ticks the same formatter wrote.
	return { value, label: `${aggregateLabels()[aggregate]} ${measure}: ${format(value)}` }
}

/** What a computed line's own label leads with. Short: it is printed on the plot. */
const aggregateLabels = translatedTable<Record<ReferenceAggregate, string>>(() => ({
	average: __('Avg'),
	median: __('Median'),
	min: __('Min'),
	max: __('Max'),
	sum: __('Sum'),
}))

function aggregateOf(aggregate: ReferenceAggregate, values: number[]): number {
	// folded, not spread: `values` is every numeric cell of every series column,
	// and a spread of those is a call with that many arguments
	if (aggregate === 'min') return values.reduce((low, value) => (value < low ? value : low))
	if (aggregate === 'max') return values.reduce((high, value) => (value > high ? value : high))

	if (aggregate === 'median') {
		const sorted = [...values].sort((a, b) => a - b)
		const middle = Math.floor(sorted.length / 2)
		// An even count has no middle value, so the two either side of it average.
		return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2
	}

	const total = values.reduce((sum, value) => sum + value, 0)
	return aggregate === 'sum' ? total : total / values.length
}

/**
 * The straight line through `points` that misses them least, by least squares.
 * A point with no value is skipped. Fewer than two points, or two at one x, fit
 * no line.
 */
export function fitLine(
	points: { x: number; y: number | null }[],
): { slope: number; intercept: number } | undefined {
	const fitted = points.filter((point): point is { x: number; y: number } => point.y !== null)
	if (fitted.length < 2) return

	const meanX = fitted.reduce((sum, p) => sum + p.x, 0) / fitted.length
	const meanY = fitted.reduce((sum, p) => sum + p.y, 0) / fitted.length
	let covariance = 0
	let variance = 0
	for (const { x, y } of fitted) {
		covariance += (x - meanX) * (y - meanY)
		variance += (x - meanX) ** 2
	}
	if (!variance) return
	const slope = covariance / variance
	return { slope, intercept: meanY - slope * meanX }
}

/**
 * Each series' trend line, as its `markLine`, keyed by column.
 *
 * v2 draws a reference line as a rule at one value, and a trend line has two ends
 * at different heights. So it rides the series it fits, through the series'
 * `echartOptions`, and takes the series' own color: a split's lines each take
 * their split's. Riding the series, it sits on that series' axis, and the legend
 * hides it with the series. `silent` keeps it out of the tooltip and the click.
 * The dash, weight and label plate are v2's for a reference line.
 *
 * It fits the points where the axis plots them: a date at its time, a number at
 * its value, as v2's `plotRows` places them. So a skipped period is a gap and
 * the author's sort does not move the line.
 */
function trendLinesFor(
	config: MixedChartConfig,
	columns: string[],
	rows: QueryResultRow[],
	horizontal: boolean,
	axisOf: (column: string) => ChartValueAxisOptions | undefined,
	tokens?: ChartTokens,
): Map<string, Record<string, any>> {
	const dimension = config.x_axis?.dimension
	const lines = new Map<string, Record<string, any>>()
	// placing every row is the cost, so a chart with no trend line pays none of it
	if (!dimension || !columns.length) return lines
	const type = plottedXAxisType(dimension, horizontal)

	const x = dimension.dimension_name
	const place = type === 'value' ? toNumber : (value: any) => toDate(value)?.getTime() ?? null
	const placed = rows.flatMap((row) => {
		const at = place(row[x])
		return at === null ? [] : [{ row, at }]
	})

	for (const column of columns) {
		const points = placed.map(({ row, at }) => ({ x: at, y: toNumber(row[column]) }))
		const fit = fitLine(points)
		if (!fit) continue

		// from the smallest x the series plots to the largest, cut to the value
		// axis: echarts drops a line with an end off it, and does not widen the
		// axis to take it
		const plotted = points.filter(
			(point): point is { x: number; y: number } => point.y !== null,
		)
		const xs = plotted.map((point) => point.x)
		const range = valueRange(
			plotted.map((point) => point.y),
			axisOf(column),
		)
		const ends = clipLine(
			fit,
			[
				xs.reduce((low, at) => (at < low ? at : low)),
				xs.reduce((high, at) => (at > high ? at : high)),
			],
			range,
		)
		if (!ends) continue
		const coord = ([at, value]: number[]) => (horizontal ? [value, at] : [at, value])
		const label = __('{0} trend', seriesLabel(column))
		const start = {
			coord: coord(ends[0]),
			lineStyle: dashedLine(REFERENCE_LINE_WIDTH),
			label: {
				show: true,
				position: 'insideEndTop',
				formatter: () => label,
				fontSize: DATA_LABEL_FONT_SIZE,
				backgroundColor: tokens
					? `color-mix(in srgb, ${tokens.backdrop} ${LABEL_PLATE_OPACITY}%, transparent)`
					: undefined,
				padding: LABEL_PADDING,
			},
		}
		const end = { coord: coord(ends[1]) }
		lines.set(column, { silent: true, symbol: 'none', data: [[start, end]] })
	}
	return lines
}

/**
 * The values a series' axis always shows: from the bound the axis was handed,
 * else from zero or the series' lowest value, to the bound it was handed, else
 * to zero or its highest. The axis may reach further for another series, never
 * less far.
 */
function valueRange(values: number[], axis?: ChartValueAxisOptions): [number, number] {
	const low = values.reduce((least, value) => (value < least ? value : least), 0)
	const high = values.reduce((most, value) => (value > most ? value : most), 0)
	return [
		typeof axis?.min === 'number' ? axis.min : low,
		typeof axis?.max === 'number' ? axis.max : high,
	]
}

/**
 * The part of the fitted line between `from` and `to` on x that stays inside
 * `range` on y, as its two ends. Each end moves along the line, so the slope
 * holds. None when the line never enters the range.
 */
function clipLine(
	fit: { slope: number; intercept: number },
	[from, to]: [number, number],
	[low, high]: [number, number],
): [number[], number[]] | undefined {
	const y = (x: number) => fit.intercept + fit.slope * x
	// The fit is float arithmetic, so a flat series fits a hair off its own
	// value, which is a bound of the range. The range is tested a hair wider,
	// and each end then set on the bound it passed.
	const hair = 1e-9 * Math.max(1, Math.abs(low), Math.abs(high))
	const [wideLow, wideHigh] = [low - hair, high + hair]
	let start = from
	let end = to
	if (fit.slope) {
		const atLow = (wideLow - fit.intercept) / fit.slope
		const atHigh = (wideHigh - fit.intercept) / fit.slope
		start = Math.max(start, Math.min(atLow, atHigh))
		end = Math.min(end, Math.max(atLow, atHigh))
	} else if (y(from) < wideLow || y(from) > wideHigh) {
		return
	}
	if (start > end) return
	const clamp = (value: number) => Math.min(high, Math.max(low, value))
	return [
		[start, clamp(y(start))],
		[end, clamp(y(end))],
	]
}

/**
 * Whether `series` takes a trend line: the form offers the toggle, and the
 * adapter draws one, on this answer alone.
 *
 * The x axis must be a scale. A category axis sits its rows in the order they
 * arrive, which may be a ranking, so a line through them says nothing. And v2
 * must not stack the series with another: it plots a stacked series at its stack
 * height or its share, and the fit reads the series' own values.
 */
export function takesTrendLine(
	config: MixedChartConfig,
	series: Series,
	mark: ChartMark,
	horizontal: boolean,
): boolean {
	if (plottedXAxisType(config.x_axis?.dimension, horizontal) === 'category') return false
	// the chart's own stack, which v2 is handed, reads every Series it holds
	const stacked = Boolean(
		stackingFor(config.y_axis, hasBarsOnBothAxes(config.y_axis?.series, mark, horizontal)),
	)
	const all = (config.y_axis?.series || []).filter((s) => s.measure?.measure_name)
	const own = markOf(config, series, mark, horizontal)
	const others = all
		.filter((other) => other !== series)
		.map((s) => markOf(config, s, mark, horizontal))
	// A split plots the series once per value, and those stack with each other.
	// A config does not say how many values a result will hold, and a filter
	// changes it, so a split always counts as stacked.
	if (config.split_by?.dimension?.column_name) others.push(own)
	return !stacksWithAnother(stacked, own, others)
}

/**
 * Whether v2 stacks a series of `mark` with another: `stackKey` in
 * `frappe-ui/src/charts/axisChartOptions.ts`, restated because the package does
 * not export it. Marks stack among their own and a line never does, and a series
 * alone in its stack keeps its own values (`stackShares`).
 */
function stacksWithAnother(stacked: boolean, mark: ChartMark, others: ChartMark[]): boolean {
	return stacked && mark !== 'line' && others.includes(mark)
}

/**
 * What a Series plots as: its own mark, else the chart's, and a line with its
 * area filled is an area. A horizontal chart draws every series as a bar, as
 * v2's `resolveMark` in `frappe-ui/src/charts/axisChartCommon.ts` does: its
 * value axis runs across the plot, and only bars are drawn against it.
 */
function markOf(
	config: MixedChartConfig,
	series: Series | undefined,
	mark: ChartMark,
	horizontal: boolean,
): ChartMark {
	if (horizontal) return 'bar'
	const line = (config.y_axis || {}) as YAxisLine
	// The form wrote 'Line' where the type declares 'line'.
	// `insights.patches.normalize_chart_configs` folded the stored ones. A config
	// an import delivers must still not silently plot the chart's own mark.
	const asked = (series?.type?.toLowerCase() as ChartMark) || mark
	const area = asked === 'line' && ((series as SeriesLine)?.show_area ?? line.show_area)
	return area ? 'area' : asked
}

/**
 * The axis the x column is plotted on, as v2 resolves it (`resolveXAxis` in
 * `frappe-ui/src/charts/axisChartCommon.ts`): a horizontal bar chart has no
 * scale to put a number on, so it draws one as categories.
 */
function plottedXAxisType(
	dimension: Dimension | undefined,
	horizontal: boolean,
): 'category' | 'time' | 'value' {
	const type = dimension ? xAxisFor(dimension).type || 'category' : 'category'
	return type === 'value' && horizontal ? 'category' : type
}

/**
 * Where a scaled axis puts a date: v2's `toDate` in
 * `frappe-ui/src/charts/format.ts`, restated because the package does not
 * export it. `plotRows` places a row at this time, and drops one without it.
 */
function toDate(value: any): Date | null {
	if (value instanceof Date) return isNaN(value.getTime()) ? null : value
	if (typeof value !== 'string' || !ISO_DATE.test(value)) return null
	const parsed = new Date(value)
	return isNaN(parsed.getTime()) ? null : parsed
}
const ISO_DATE = /^\d{4}-\d{2}(-\d{2})?([T ]\d{2}:\d{2}(:\d{2})?)?/

/**
 * What the legend calls a series: v2's `seriesLabel` over a column with no label
 * of its own, which is `formatLabel` in `frappe-ui/src/charts/format.ts`. The
 * package exports neither, so the rule is restated here.
 */
function seriesLabel(column: string) {
	return column
		.split('_')
		.map((word) => word.charAt(0).toUpperCase() + word.slice(1))
		.join(' ')
}

// v2's reference-line style, in `frappe-ui/src/charts/referenceLines.ts`. The
// package exports none of it, so the values are restated here.
const REFERENCE_LINE_WIDTH = 1
const DATA_LABEL_FONT_SIZE = 11
const LABEL_PADDING = [2, 4]
const LABEL_PLATE_OPACITY = 80

/** v2's `dashedLine`: dash and gap in multiples of the width. */
function dashedLine(width: number) {
	return { type: [width * 3.5, width * 3], width }
}
