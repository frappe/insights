import { AXIS_CHARTS, ChartConfig } from '../types/chart.types'

// What a Chart's config needs doing to it before anything reads it. Drawing is
// not here: the adapter turns a config into chart props, and frappe-ui draws
// them.

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

// Every chart type reads a fixed set of slots off the config, and the validator and the
// config forms reach into them without guarding. A type switch replaces the config
// wholesale, so the incoming type's slots have to exist before anything reads them.
//
// This runs on load, before the document baseline is set. A config form that wrote
// its own slots when it mounted would leave every chart dirty for being opened —
// one autosave and two re-runs of the chart data.
//
// It writes only a slot the config does not have, because an empty list is what
// its author left.
export function ensureConfigSlots(config: any, chart_type: string) {
	// A config that already names a series was authored, whatever it left unset.
	const authored = Boolean(config.y_axis?.series?.length)

	if (AXIS_CHARTS.includes(chart_type)) {
		config.x_axis = config.x_axis || {}
		config.x_axis.dimension = config.x_axis.dimension || {}
		config.y_axis = config.y_axis || {}
		// one empty series, so a chart that names no axis opens on a picker
		// rather than on nothing
		config.y_axis.series = config.y_axis.series || [{ measure: {} }]
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
		// one empty value, so a card that names no reading opens on a picker
		// rather than on nothing
		config.number_columns = config.number_columns || [{}]
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
		config.rows = config.rows || [{}]
		config.columns = config.columns || [{}]
		config.values = config.values || [{}]
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
// them. The chart store runs it on load, and the view endpoint's config runs it
// too — a card drawn on a desk page and the same card in the builder must not
// disagree about what an old chart looks like.
//
// It only fills in what a config does not say. The server rewrites every older
// shape where it is stored, because a repair on load lands in the author's next
// save as an edit the author never made. See `normalize_chart_config` in
// `chart_query.py`.
export function normalizeChartConfig(config: any, chart_type: string) {
	config.order_by = config.order_by || []
	config.limit = config.limit || 100
	config.filters = config.filters?.filters?.length
		? config.filters
		: { filters: [], logical_operator: 'And' }

	config = ensureConfigSlots(config, chart_type)
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

export function getGranularity(dimension_name: string, config: ChartConfig) {
	const dimension = configDimensions(config).find(
		(candidate) => candidate.dimension_name === dimension_name,
	)
	return dimension?.granularity
}
