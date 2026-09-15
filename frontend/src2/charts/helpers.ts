import { getUniqueId } from '../helpers'
import { AXIS_CHARTS, AxisChartConfig, ChartConfig } from '../types/chart.types'

// What a Chart's config needs doing to it before anything reads it. Drawing is
// not here: the adapter turns a config into chart props, and frappe-ui draws
// them.

export function handleOldXAxisConfig(old_x_axis: any): AxisChartConfig['x_axis'] {
	if (old_x_axis && old_x_axis.column_name) {
		return {
			dimension: old_x_axis,
		}
	}
	return old_x_axis
}

export function handleOldYAxisConfig(old_y_axis: any): AxisChartConfig['y_axis'] {
	if (Array.isArray(old_y_axis)) {
		return {
			series: old_y_axis.map((measure: any) => ({ measure })),
		}
	}
	return old_y_axis
}

// `statistic` is what develop called a computed reference line before this
// branch named it `aggregate`. It read every plotted number on the axis, so it
// never named a Measure. The nearest Measure here is the first series that
// axis draws.
export function handleOldReferenceLines(config: any) {
	const lines = config?.y_axis?.reference_lines
	if (!Array.isArray(lines)) return config

	const series = config.y_axis.series || []
	for (const line of lines) {
		// What the form keys its rows on. A line saved before the id existed gets
		// one here, so the key is stable from the first render.
		if (!line.id) line.id = getUniqueId()
		if (!line.statistic) {
			delete line.statistic
			continue
		}
		if (!line.aggregate) {
			const align = line.align === 'Right' ? 'Right' : 'Left'
			const target = series.find((s: any) => (s.align || 'Left') === align) || series[0]
			const measure_name = target?.measure?.measure_name
			if (measure_name) {
				line.aggregate = line.statistic
				line.measure_name = measure_name
				line.axis = 'y'
			}
		}
		delete line.statistic
	}
	return config
}

// `hide_from_chart` marked a series drawn at zero opacity and filtered out of
// the legend, which left its value reaching the tooltip and nothing else. That
// is what `tooltip.measures` says, so the flag moves there rather than
// staying a second way to say one thing.
//
// A chart that hid every series is left alone. Moving them all would leave the
// adapter no value column to plot, and it draws nothing at all rather than an
// empty plot. Those charts keep the flag, which nothing reads any more, so they
// draw every series instead of none — a degenerate chart either way, and the
// one that shows its data is the better of the two.
export function handleOldHideFromChart(config: any) {
	const series = config?.y_axis?.series
	if (!Array.isArray(series)) return config

	const hidden = series.filter((s: any) => s?.hide_from_chart)
	if (!hidden.length || hidden.length === series.length) return config

	// The flag is read, never written: it stays on the measure that moved so a
	// config saved before this release still reads the same way on the next load.
	const carried = config.tooltip?.measures || []
	const named = new Set(carried.map((measure: any) => measure?.measure_name))
	const moved = hidden
		.map((s: any) => s.measure)
		.filter((measure: any) => measure?.measure_name && !named.has(measure.measure_name))

	config.tooltip = { measures: [...carried, ...moved] }
	config.y_axis.series = series.filter((s: any) => !s?.hide_from_chart)
	return config
}

// The Y Axis form wrote 'Line' and 'Bar' where the series type declares 'line'
// and 'bar'. frappe-ui refuses a mark it does not know and draws the chart's own
// instead, so a series saved in the old case stopped drawing as itself.
export function handleOldSeriesTypes(config: any) {
	const series = config?.y_axis?.series
	if (!Array.isArray(series)) return config

	for (const serie of series) {
		if (typeof serie?.type === 'string') serie.type = serie.type.toLowerCase()
	}
	return config
}

/**
 * Whether a chart draws bars against both value axes, which is the one layout a
 * stack cannot read: the segments of one column would sum two scales. A line
 * never stacks, so bars on the left beside a line on the right still do. The
 * adapter and the config form both rule on it, so they rule through one answer.
 * Neither writes it back: a saved flag outlives a rule that is later corrected.
 *
 * `mark` is what a series with no type draws as. frappe-ui gives a horizontal
 * chart no second value axis (`hasSecondaryValueAxis`), so it never has bars on both.
 */
export function hasBarsOnBothAxes(
	series: { align?: string; type?: string }[] | undefined,
	mark: string,
	horizontal: boolean,
): boolean {
	if (horizontal) return false
	// the adapter can be handed a config the normalizer never saw, so the old 'Bar' counts too
	const bars = (series || []).filter((s) => (s?.type?.toLowerCase() || mark) === 'bar')
	return (
		bars.some((s) => (s?.align || 'Left') === 'Left') && bars.some((s) => s?.align === 'Right')
	)
}

// The Y Axis form wrote a number box's text, and a cleared box wrote ''. frappe-ui
// takes '' as a bound, because it is not absent to `??`, and pins the axis at 0.
export function handleOldAxisBounds(config: any) {
	const y_axis = config?.y_axis
	if (!y_axis || Array.isArray(y_axis)) return config

	for (const bound of ['min', 'max'] as const) {
		if (!(bound in y_axis)) continue
		const value = y_axis[bound]
		const number = Number(value)
		if (value === '' || value === null || !Number.isFinite(number)) delete y_axis[bound]
		else y_axis[bound] = number
	}
	return config
}

// Every chart type reads a fixed set of slots off the config, and the validator and the
// config forms reach into them without guarding. A type switch replaces the config
// wholesale, so the incoming type's slots have to exist before anything reads them.
//
// This runs on load, before the document baseline is set. A config form that wrote
// its own slots when it mounted would leave every chart dirty for being opened —
// one autosave and two re-runs of the chart data.
export function ensureConfigSlots(config: any, chart_type: string) {
	// A config that already names a series was authored, whatever it left unset.
	const authored = Boolean(config.y_axis?.series?.length)

	if (AXIS_CHARTS.includes(chart_type)) {
		config.x_axis = config.x_axis || {}
		config.x_axis.dimension = config.x_axis.dimension || {}
		config.y_axis = config.y_axis || {}
		// one empty series, so the form opens on a picker rather than on nothing
		config.y_axis.series = config.y_axis.series?.length
			? config.y_axis.series
			: [{ measure: {} }]
	}

	// A new bar stacks unless its author says otherwise, and the form reads the
	// flag rather than the absence of one. A chart that was authored without the
	// flag was drawn grouped, and writing the default here would restack it.
	if ((chart_type === 'Bar' || chart_type === 'Row') && !authored) {
		if (config.y_axis.stack === undefined) {
			config.y_axis.stack = true
		}
	}

	if (chart_type === 'Number') {
		// one empty value, so the form opens on a picker rather than on nothing
		config.number_columns = config.number_columns?.length ? config.number_columns : [{}]
		// A reading saved without an id takes its Measure's name: the same id on
		// every load, and the name a cell written before ids named it by.
		// `reading_id` in `resize_dashboard_cells.py` reads it the same way.
		for (const reading of config.number_columns) {
			if (reading && !reading.id) reading.id = reading.measure_name || getUniqueId()
		}
		config.number_column_options = config.number_column_options || []
		config.date_column = config.date_column || {}
	}

	if (chart_type === 'Donut') {
		config.label_column = config.label_column || {}
		config.value_column = config.value_column || {}
	}

	if (chart_type === 'Funnel') {
		config.measures = config.measures || []
		config.label_column = config.label_column || {}
		config.value_column = config.value_column || {}
	}

	if (chart_type === 'Table') {
		config.rows = config.rows?.length ? config.rows : [{}]
		config.columns = config.columns?.length ? config.columns : [{}]
		config.values = config.values?.length ? config.values : [{}]
	}

	if (chart_type === 'Map') {
		config.location_column = config.location_column || {}
		config.value_column = config.value_column || {}
	}

	if (chart_type === 'Bubble') {
		config.xAxis = config.xAxis || {}
		config.yAxis = config.yAxis || {}
		config.size_column = config.size_column || {}
	}

	if (chart_type === 'Sankey') {
		config.source_column = config.source_column || {}
		config.target_column = config.target_column || {}
		config.value_column = config.value_column || {}
	}

	if (chart_type === 'Heatmap') {
		config.x_column = config.x_column || {}
		config.y_column = config.y_column || {}
		config.value_column = config.value_column || {}
	}

	return config
}

/** The single-Dimension slots a config can carry, over every chart type. */
const DIMENSION_SLOTS = [
	'date_column',
	'label_column',
	'source_column',
	'target_column',
	'x_column',
	'y_column',
	'dimension',
	'quadrant_column',
	'location_column',
]

/**
 * Every Dimension a config carries, in whichever slot holds it.
 *
 * The one walk over the slots. A chart type that adds a single-Dimension slot
 * adds it to `DIMENSION_SLOTS` and every reader here follows: a slot one reader
 * knows and another does not is a grain the app offers and cannot store.
 */
export function configDimensions(config: any): any[] {
	const dimensions: any[] = []
	const collect = (dimension: any) => {
		if (dimension && typeof dimension === 'object') dimensions.push(dimension)
	}

	collect(config.x_axis?.dimension)
	collect(config.split_by?.dimension)
	for (const slot of DIMENSION_SLOTS) collect(config[slot])
	for (const list of [config.rows, config.columns]) {
		if (Array.isArray(list)) list.forEach(collect)
	}

	return dimensions
}

/** The single-Measure slots a config can carry, over every chart type. */
const MEASURE_SLOTS = ['value_column', 'size_column', 'xAxis', 'yAxis']

/** The Measure-list slots a config can carry, over every chart type. */
const MEASURE_LIST_SLOTS = ['number_columns', 'measures', 'values']

/**
 * Every Measure a config carries, in whichever slot holds it.
 *
 * The counterpart to `configDimensions`, and the same rule: a chart type that
 * adds a Measure slot adds it here and every reader follows.
 */
export function configMeasures(config: any): any[] {
	const measures: any[] = []
	const collect = (measure: any) => {
		if (measure && typeof measure === 'object') measures.push(measure)
	}

	for (const serie of config.y_axis?.series || []) collect(serie?.measure)
	for (const measure of config.tooltip?.measures || []) collect(measure)
	for (const slot of MEASURE_SLOTS) collect(config[slot])
	for (const slot of MEASURE_LIST_SLOTS) {
		if (Array.isArray(config[slot])) config[slot].forEach(collect)
	}

	return measures
}

/**
 * The half of a chart's config that decides which rows come back.
 *
 * A Dimension and a Measure are the selection, whichever slot holds them, and
 * the rest of the question is the filters, the sort, the caps and — for a Number
 * card — the period and what each reading is measured against. A color, a mark,
 * an axis label and a number format are the other half: they say how the rows are
 * drawn, and drawing them again is free.
 *
 * `docs/adr/type-independent-chart-config.md` names this boundary as the shape
 * the config is going to; until it arrives, this reads it out of the slots.
 */
export function dataSelection(config: any) {
	if (!config || typeof config !== 'object') return config
	return {
		dimensions: configDimensions(config),
		measures: configMeasures(config),
		filters: config.filters,
		order_by: config.order_by,
		limit: config.limit,
		// a Number card's period, and the span each reading is compared against:
		// both are stretches of rows the server fetches
		window: config.window,
		sparkline: config.sparkline,
		readings: (config.number_column_options || []).map((option: any) => ({
			target: option?.target,
			comparison: option?.comparison,
		})),
		// how many series a split may draw, and how many columns a pivot may make:
		// both are bounded in SQL
		max_split_values: config.split_by?.max_split_values,
		max_column_values: config.max_column_values,
	}
}

export function setDimensionNames(config: any) {
	for (const dimension of configDimensions(config)) {
		if (!dimension.dimension_name && dimension.column_name) {
			dimension.dimension_name = dimension.column_name
		}
	}
	return config
}

/**
 * What a chart keeps when its author takes the options back: the rows that come
 * back, and nothing about how they are drawn. `filters` and `limit` are the half
 * of the config that decides which rows those are, so a reset leaves them as
 * they stand and refills the slots the new type reads.
 */
export function resetChartConfig(config: any, chart_type: string) {
	return ensureConfigSlots(
		{ order_by: [], filters: config.filters, limit: config.limit },
		chart_type,
	)
}

// Every saved config passes through here before anything reads it: the slots are
// read without guarding, and a config saved by an older version may not have
// them. The chart store runs it on load, and the viewer endpoint's config runs it
// too — a card drawn on a desk page and the same card in the builder must not
// disagree about what an old chart looks like.
export function normalizeChartConfig(config: any, chart_type: string) {
	config.order_by = config.order_by || []
	config.limit = config.limit || 100
	config.filters = config.filters?.filters?.length
		? config.filters
		: { filters: [], logical_operator: 'And' }

	if ('x_axis' in config && config.x_axis) {
		config.x_axis = handleOldXAxisConfig(config.x_axis)
	}
	if ('y_axis' in config && Array.isArray(config.y_axis)) {
		config.y_axis = handleOldYAxisConfig(config.y_axis)
	}
	if ('split_by' in config && config.split_by) {
		config.split_by = handleOldXAxisConfig(config.split_by)
	}
	if (chart_type === 'Number') {
		config = handleOldNumberShapes(config)
	}

	config = setDimensionNames(config)
	config = handleOldHideFromChart(config)
	config = handleOldAxisBounds(config)
	config = ensureConfigSlots(config, chart_type)
	config = handleOldReferenceLines(config)
	config = handleOldSeriesTypes(config)
	return config
}

/**
 * A Number card's readings and their options are paired by position — the
 * reading at index 2 is drawn with `number_column_options[2]`, and its target
 * and its comparison are what the server is asked to resolve for it. Nothing
 * downstream can recover the pairing, so whoever writes the order writes both
 * arrays, here.
 *
 * An option is written only where an author set one, so the array can be
 * shorter than the readings it answers for. Both acts pad it first, or a splice
 * lands on an index that is not there and the pairing slides by one.
 */
function paddedNumberOptions(config: any) {
	const options = config.number_column_options || (config.number_column_options = [])
	while (options.length < (config.number_columns?.length || 0)) options.push({})
	return options
}

/** Take one reading off the card, options and all. */
export function removeNumberReading(config: any, index: number) {
	paddedNumberOptions(config).splice(index, 1)
	config.number_columns.splice(index, 1)
}

/**
 * Move one reading's options to where the reading went.
 *
 * The readings themselves are moved by whoever reordered them — the draggable
 * list moves the array it is bound to and reports the move.
 */
export function moveNumberReadingOptions(config: any, from: number, to: number) {
	const options = paddedNumberOptions(config)
	options.splice(to, 0, options.splice(from, 1)[0])
}

/**
 * A Number card's period, and every reading's target, comparison and direction,
 * written where the card reads them.
 *
 * Three releases have written what a reading is measured against and two have
 * written the period it reads. The server reads every one of those shapes —
 * `normalize_number_shapes` in `chart_query.py` — and so does the renderer here,
 * because a config can still arrive in an old shape after the patch has run: an
 * import, or a template another app ships.
 */
export function handleOldNumberShapes(config: any) {
	// the chart-level flag: one comparison, on every reading, against the period
	// before this one
	const flag = config.comparison
	delete config.comparison

	// the other chart-level flag: which way is up, once, for every reading
	const better = config.negative_is_better
	delete config.negative_is_better

	raisePeriod(config)

	const columns = config.number_columns || []
	const options = Array.isArray(config.number_column_options) ? config.number_column_options : []

	columns.forEach((_: any, index: number) => {
		while (options.length <= index) options.push({})
		const beside = options[index] && typeof options[index] === 'object' ? options[index] : {}
		options[index] = beside

		// a reading that said which way is up already overrode the chart, so the
		// chart's flag only fills the ones that said nothing
		if (better && beside.negative_is_better === undefined) beside.negative_is_better = better

		const measured = measuredAgainst(beside, flag)
		delete beside.references
		for (const key of ['target', 'comparison'] as const) {
			if (measured[key] && !beside[key]) beside[key] = measured[key]
		}

		normalizeComparison(beside)
	})

	if (columns.length) config.number_column_options = options
	return config
}

/**
 * The period the card reads, moved off the date column and onto the chart. A
 * granularity on the date column used to group the card, and `window` does that
 * now — both at once would group twice.
 */
function raisePeriod(config: any) {
	const date_column = config.date_column
	if (!date_column || typeof date_column !== 'object' || !date_column.granularity) return

	const window = config.window || {}
	if (!window.span && !window.grain) {
		config.window = { ...window, grain: date_column.granularity }
	}
	delete date_column.granularity
}

/**
 * A period comparison, written as the question it asks. The shift it carried was
 * decided by the period the card read at the time, and the period decides it
 * where the card is read now.
 */
function normalizeComparison(options: any) {
	const comparison = options.comparison
	if (!comparison || typeof comparison !== 'object' || comparison.source !== 'window') return

	const shift = comparison.shift || {}
	delete comparison.shift
	const yearBack = ['year', 'fiscal year'].includes(shift.unit) && shift.count === -1
	comparison.source = yearBack ? 'last year' : 'previous'
}

/** What the reading is measured against: what it names, else the `references` it
 * named, else the chart's flag. */
function measuredAgainst(options: any, flag: any): { target?: any; comparison?: any } {
	if (options.target || options.comparison) return {}
	if (Array.isArray(options.references)) return fromReferences(options.references)
	return flag ? { comparison: { source: 'previous' } } : {}
}

/** A movement in the list is the comparison, an attainment the target. */
function fromReferences(references: any[]): { target?: any; comparison?: any } {
	const moves = (reference: any) =>
		['change', 'delta'].includes(reference.show) || reference.source === 'previous'

	const list = references.filter((reference) => reference && typeof reference === 'object')
	const leading = list.findIndex(moves)
	const aim = list.findIndex(
		(reference, index) => index !== leading && reference.show === 'attainment',
	)

	const measured: { target?: any; comparison?: any } = {}
	if (leading !== -1) {
		const reference = list[leading]
		const comparison: any = { source: reference.source }
		if (reference.value !== undefined && reference.value !== null)
			comparison.value = reference.value
		if (reference.measure) comparison.measure = reference.measure
		comparison.show = reference.show === 'delta' ? 'delta' : 'change'
		if (reference.label) comparison.label = reference.label
		measured.comparison = comparison
	}
	if (aim !== -1) {
		const reference = list[aim]
		measured.target = reference.measure
			? { measure: reference.measure }
			: { value: reference.value }
	}
	return measured
}

export function getGranularity(dimension_name: string, config: ChartConfig) {
	const dimension = configDimensions(config).find(
		(candidate) => candidate.dimension_name === dimension_name,
	)
	return dimension?.granularity
}
