// A click reduces to a set of segment filters — the dimension values it pins, as
// (column, operator, literal) triples against the query's pre-summarize surface.
// A number card pins the empty set. Nothing past `segmentOf` reads a chart type.

import { computed, reactive, shallowRef } from 'vue'
import { FIELDTYPES, getGranularityOptions } from '../../helpers/constants'
import { getFormattedDate } from '../../query/helpers'
import { AXIS_CHARTS } from '../../types/chart.types'
import type {
	AxisChartConfig,
	BubbleChartConfig,
	ChartConfig,
	ChartType,
	DonutChartConfig,
	FunnelChartConfig,
	HeatmapChartConfig,
	MapChartConfig,
	NumberChartConfig,
	SankeyChartConfig,
	TableChartConfig,
} from '../../types/chart.types'
import type {
	ColumnDataType,
	Dimension,
	FilterOperator,
	Measure,
	Operation,
	QueryResultColumn,
	QueryResultRow,
} from '../../types/query.types'
import type { DrillDownTarget } from '../adapter'
import type { RecordLinks } from '../record_link'

// ---------------------------------------------------------------------------
// The wire shapes. Everything the server is told, and nothing it is not.
// ---------------------------------------------------------------------------

/** One pinned dimension value. Literals only — no operations cross the wire. */
export type DrillFilter = {
	column: string
	operator: FilterOperator
	value: string | number
}

/**
 * What a level does with its segment. Both carry the Measure the click landed
 * on, because a Measure can carry a condition of its own.
 *
 * The server picks a granularity when this field is absent. A granularity set
 * here overrides the server's choice. The first response writes its granularity
 * back onto the level.
 */
export type DrillAction =
	| { breakdown: string; measure?: string; granularity?: string }
	| { records: true; measure?: string }

export type DrillLevel = {
	segment_filters: DrillFilter[]
	action: DrillAction
}

/** A candidate for "break down by", as `get_chart_data` reports it. */
export type DrillDimension = {
	name: string
	type: ColumnDataType
}

// ---------------------------------------------------------------------------
// The descriptor a click produces
// ---------------------------------------------------------------------------

/**
 * One pinned value: the column it holds, and the value as a reader reads it.
 *
 * Both halves, because a value alone does not say what it is a value of. "FY
 * 2024-25" and "Lighting" name no columns, and a reader three levels down has
 * no way left to ask.
 */
export type DrillPin = {
	column: string
	value: string
}

/** What a segment click pins, before the reader has said what to do with it. */
export type DrillSegment = {
	/** The pins, as the wire carries them. Empty for a number card. */
	filters: DrillFilter[]
	/**
	 * What this segment pins. The columns are subtracted from the breakdown
	 * candidates, and the values are what the reader is shown.
	 */
	pins: DrillPin[]
	/** The result column clicked, reduced to the Measure behind it. */
	measure?: string
}

/** A Chart as the drill reads it: the slots its type declares, and its type. */
export type DrillChart = {
	chart_type: ChartType
	config: ChartConfig
}

/**
 * The Dimensions a Chart's type declares, split by where a click reads their
 * value from: a row Dimension's value stands in the clicked row, a column
 * Dimension's stands in the clicked column's *name* (that is what a pivot is).
 */
type DeclaredDimensions = {
	rows: Dimension[]
	columns: Dimension[]
	/**
	 * Declared, but not identified by a click: a number card's date column groups
	 * the readings behind the card and a click on the card pins none of them. It
	 * is still one of the Chart's own Dimensions, so it leads the candidates.
	 */
	unpinned: Dimension[]
	measures: Measure[]
}

/** A config slot is a slot whether or not the author has filled it in. */
const dims = (slots: (Dimension | undefined)[]): Dimension[] =>
	slots.filter((slot): slot is Dimension => Boolean(slot?.column_name))

const nums = (slots: (Measure | undefined)[]): Measure[] =>
	slots.filter((slot): slot is Measure => Boolean(slot?.measure_name))

/**
 * The one place a chart type is read. Everything downstream works off the
 * answer, so a new type is added here and nowhere else.
 */
function declaredDimensions(chart: DrillChart): DeclaredDimensions {
	const config = chart.config as any
	const empty: DeclaredDimensions = { rows: [], columns: [], unpinned: [], measures: [] }

	if (AXIS_CHARTS.includes(chart.chart_type)) {
		const axis = config as AxisChartConfig
		return {
			...empty,
			rows: dims([axis.x_axis?.dimension]),
			columns: dims([axis.split_by?.dimension]),
			measures: nums((axis.y_axis?.series || []).map((series) => series.measure)),
		}
	}

	switch (chart.chart_type) {
		case 'Donut': {
			const donut = config as DonutChartConfig
			return {
				...empty,
				rows: dims([donut.label_column]),
				measures: nums([donut.value_column]),
			}
		}
		case 'Funnel': {
			const funnel = config as FunnelChartConfig
			// Two modes: one stage per Measure, or one stage per row of a Dimension.
			return {
				...empty,
				rows: dims([funnel.label_column]),
				measures: nums(funnel.measures?.length ? funnel.measures : [funnel.value_column]),
			}
		}
		case 'Table': {
			const table = config as TableChartConfig
			return {
				...empty,
				rows: dims(table.rows || []),
				columns: dims(table.columns || []),
				measures: nums(table.values || []),
			}
		}
		case 'Map': {
			const map = config as MapChartConfig
			return {
				...empty,
				rows: dims([map.location_column]),
				measures: nums([map.value_column]),
			}
		}
		case 'Bubble': {
			const bubble = config as BubbleChartConfig
			// The group is part of what names the point, not a slot beside it: the
			// row a point was drawn from carries its value like any other Dimension.
			return {
				...empty,
				rows: dims([bubble.dimension, bubble.quadrant_column]),
				measures: nums([bubble.xAxis, bubble.yAxis, bubble.size_column]),
			}
		}
		case 'Sankey': {
			const sankey = config as SankeyChartConfig
			return {
				...empty,
				rows: dims([sankey.source_column, sankey.target_column]),
				measures: nums([sankey.value_column]),
			}
		}
		case 'Heatmap': {
			const heatmap = config as HeatmapChartConfig
			// A cell stands for one pair, so a click pins both of the grid's cuts.
			return {
				...empty,
				rows: dims([heatmap.x_column, heatmap.y_column]),
				measures: nums([heatmap.value_column]),
			}
		}
		case 'Number': {
			const number = config as NumberChartConfig
			return {
				...empty,
				unpinned: dims([number.date_column]),
				measures: nums(number.number_columns || []),
			}
		}
		default:
			return empty
	}
}

/**
 * A query builder's own result, read as a Chart. The last aggregating step says
 * which columns a click pins, so it is read straight into a Table config.
 *
 * @returns undefined when nothing in the pipeline aggregates.
 */
export function queryResultChart(operations: Operation[]): DrillChart | undefined {
	const aggregating = operations.filter(
		(operation) => operation.type === 'summarize' || operation.type === 'pivot_wider',
	)
	const step = aggregating[aggregating.length - 1]
	if (!step) return

	const config: TableChartConfig =
		step.type === 'summarize'
			? { rows: step.dimensions, columns: [], values: step.measures }
			: { rows: step.rows, columns: step.columns, values: step.values }

	return { chart_type: 'Table', config }
}

/** Every Dimension column a Chart declares, in declaration order. */
export function declaredDimensionColumns(chart: DrillChart): string[] {
	const declared = declaredDimensions(chart)
	return [...declared.rows, ...declared.columns, ...declared.unpinned].map(
		(dimension) => dimension.column_name,
	)
}

/**
 * A pivoted column carries the split's values in its own name. The Measure
 * comes first and the Dimension values follow it in declaration order, which is
 * how the server names them — so the *trailing* parts are the values, however
 * many Dimensions the pivot has, and whatever is left in front is the Measure.
 * A single Measure is not named at all, and the config is the only place left
 * that knows it.
 */
function readPivotedColumn(
	column: string,
	columnDimensions: Dimension[],
	measures: Measure[],
): { values: string[]; measure?: string } {
	if (!columnDimensions.length) return { values: [], measure: column }

	const parts = column.split('___')
	const values = parts.slice(-columnDimensions.length)
	const head = parts.slice(0, -columnDimensions.length)
	const measure = head.length ? head.join('___') : measures[0]?.measure_name
	return { values, measure }
}

/**
 * One pin: the value, as it stands in the row.
 *
 * A date grouped by a grain names a bucket rather than a moment, and the span
 * that bucket covers is worked out where the grain lives — in the pipeline the
 * server slices. The client says what was clicked and nothing about how to
 * match it, which is the whole point of sending literals.
 */
function filterForDimension(dimension: Dimension, value: any): DrillFilter {
	const column = dimension.column_name

	// A segment standing for the rows that have no value is a real segment, and
	// `= NULL` matches none of them.
	if (value === null || value === undefined) {
		return { column, operator: 'is_not_set', value: '' }
	}

	return { column, operator: '=', value }
}

function labelForDimension(dimension: Dimension, value: any): string {
	if (value === null || value === undefined || value === '') return '(blank)'
	if (FIELDTYPES.DATE.includes(dimension.data_type) && dimension.granularity) {
		return getFormattedDate(String(value), dimension.granularity)
	}
	return String(value)
}

/**
 * The descriptor a segment click produces.
 *
 * `target.row` is the **raw** row the chart was clicked with — the surfaces that
 * draw formatted rows cross back themselves. A filter built from a printed value
 * would not match anything the query can be asked about.
 */
export function segmentOf(chart: DrillChart, target: DrillDownTarget): DrillSegment {
	const declared = declaredDimensions(chart)
	const pivot = readPivotedColumn(target.column, declared.columns, declared.measures)

	const filters: DrillFilter[] = []
	const pins: DrillPin[] = []

	const pin = (dimension: Dimension, value: any) => {
		filters.push(filterForDimension(dimension, value))
		pins.push({ column: dimension.column_name, value: labelForDimension(dimension, value) })
	}

	for (const dimension of declared.rows) {
		pin(dimension, target.row?.[dimension.dimension_name])
	}

	declared.columns.forEach((dimension, index) => {
		const value = pivot.values[index]
		if (value === undefined) return
		pin(dimension, value)
	})

	return { filters, pins, measure: pivot.measure }
}

/**
 * The grain a records level's date columns are printed at.
 *
 * A records level groups nothing, so its dates carry no grain of their own.
 * The column's own type is the honest grain there: a `Date` is a day, a
 * `Datetime` is a moment. A grouped date is a different reading, and the chart
 * that draws it is told the grain directly.
 */
export function recordDateGranularity(columns: QueryResultColumn[]): Record<string, string> {
	const byType: Record<string, string> = { Date: 'day', Datetime: 'second', Time: 'second' }

	const granularity: Record<string, string> = {}
	for (const column of columns) {
		if (byType[column.type]) granularity[column.name] = byType[column.type]
	}
	return granularity
}

/**
 * A pre-summarize column as a reader reads it. These are the query's own column
 * names, which are field names more often than they are words.
 */
export function columnLabel(name: string): string {
	return name
		.replace(/_/g, ' ')
		.split(' ')
		.filter(Boolean)
		.map((word) => word.charAt(0).toUpperCase() + word.slice(1))
		.join(' ')
}

/**
 * What "Break down by" offers: the pre-summarize Dimensions the response
 * carried, less every column the stack has pinned — this click's, and the ones
 * the levels above it fixed. The Chart's own other Dimensions come first — a
 * reader reaches for a column the chart already talks about — and the rest
 * follow alphabetically.
 */
export function breakdownCandidates(
	available: DrillDimension[],
	pins: string[],
	declared: string[],
): DrillDimension[] {
	const pinned = new Set(pins)
	const rank = new Map(declared.filter((name) => !pinned.has(name)).map((name, i) => [name, i]))

	return available
		.filter((dimension) => !pinned.has(dimension.name))
		.sort((a, b) => {
			const left = rank.has(a.name) ? rank.get(a.name)! : Infinity
			const right = rank.has(b.name) ? rank.get(b.name)! : Infinity
			if (left !== right) return left - right
			return a.name.localeCompare(b.name)
		})
}

/**
 * The grains a breakdown column can be read at.
 *
 * The candidates carry each column's type, so the grains a reader may ask for
 * are known without another call — and they are the grains the rest of the app
 * offers for that type, not a list of the drill's own. Empty for anything that
 * is not a date, which is also every breakdown that comes back ranked.
 */
export function grainsFor(dimensions: DrillDimension[], column: string) {
	return getGranularityOptions(dimensions.find((candidate) => candidate.name === column)?.type)
}

// ---------------------------------------------------------------------------
// The stack
// ---------------------------------------------------------------------------

/** One level, plus the two things only the reader needs: its crumb and its pins. */
export type DrillEntry = {
	level: DrillLevel
	/** what the reader clicked to get here. Empty when it pins nothing. */
	pins: DrillPin[]
	/** what this level does — "by Region", "Records" */
	actionLabel: string
}

/**
 * One crumb of the stack: one level, and the depth clicking it pops to.
 *
 * Only what a level *does* is a crumb. The value it was reached through is a
 * pin, and the two used to sit in one trail — where "Overdue" and "by Region"
 * both carried depth 1, so half the trail was a link to where the link beside
 * it went. A pin is state. A crumb is a destination.
 */
export type DrillCrumb = {
	label: string
	depth: number
}

/** What the server answered for one level. Cached for the dialog's lifetime. */
export type DrillLevelData = {
	columns: QueryResultColumn[]
	rows: QueryResultRow[]
	/**
	 * Whether the Dimension this level broke down has an order of its own. The
	 * server answers it, because the cut and the reading have to agree.
	 */
	ordered?: boolean
	/** the grain an ordered breakdown was grouped by, whoever chose it */
	granularity?: string | null
	/**
	 * Whether this level's groups add up to the segment above them. The server
	 * answers it for the same reason it answers `ordered`: the response carries
	 * column types, and nothing in a column of decimals says whether they hold
	 * sums or averages.
	 */
	additive?: boolean
	/** how many rows there are behind the bounded few that came back */
	total_row_count?: number
	/** only on a records level, and only for the columns that name a document */
	record_links?: RecordLinks
	/**
	 * The pipeline the server sliced for this level, and the connection it ran
	 * on. The authoring door alone answers with them.
	 */
	operations?: Operation[]
	use_live_connection?: boolean
}

/** What the dialog drills, as the surface that opened it hands it over. */
export type DrillSubject = {
	chart: DrillChart
	/** the first crumb — what the reader clicked into */
	title: string
	dimensions: DrillDimension[]
	fetch: (levels: DrillLevel[]) => Promise<DrillLevelData>
}

/**
 * The reader's descent through one dialog. Push to go deeper, pop to retrace.
 * Each answer is held against the exact stack that produced it, so a pop asks
 * the server nothing and a re-drill gets the new level rather than the old rows.
 */
export function makeDrillStack() {
	// shallow on purpose: an entry is replaced, never edited, and the rows a
	// level answered with have no business being made reactive one cell at a time
	const entries = shallowRef<DrillEntry[]>([])
	const answers = new Map<string, DrillLevelData>()

	const levels = computed<DrillLevel[]>(() => entries.value.map((entry) => entry.level))
	const signature = () => JSON.stringify(levels.value)

	const crumbs = computed<DrillCrumb[]>(() =>
		entries.value.map((entry, index) => ({ label: entry.actionLabel, depth: index + 1 })),
	)

	// Everything the stack has pinned, in the order it was pinned. A level whose
	// segment pins nothing contributes none, which is what a click on a number
	// card does.
	const pins = computed<DrillPin[]>(() => entries.value.flatMap((entry) => entry.pins))

	/**
	 * Read the level the reader is standing on at another grain. It replaces the
	 * level rather than pushing one, so the way back out does not change. The
	 * answer already held stays where it is, under the level as it was asked then.
	 */
	function regrain(granularity: string) {
		const entry = entries.value[entries.value.length - 1]
		const action = entry?.level.action
		if (!action || !('breakdown' in action)) return
		if (action.granularity === granularity) return

		const regrained = {
			...entry,
			level: { ...entry.level, action: { ...action, granularity } },
		}
		entries.value = [...entries.value.slice(0, -1), regrained]
	}

	return reactive({
		entries,
		/** exactly what `get_drill_data` is sent */
		levels,
		depth: computed(() => entries.value.length),
		current: computed(() => entries.value[entries.value.length - 1]),
		/**
		 * Everything the stack has pinned, read in order.
		 *
		 * They are read, never clicked: the levels under a pin were reached
		 * through it, so dropping one is not dropping a filter, it is re-rooting
		 * the stack. That move is the crumb for that level.
		 */
		pins,
		/**
		 * The columns those pins hold. A Dimension already pinned upstream is not
		 * a way of splitting anything further down, so the menu stops offering it
		 * as the reader descends.
		 */
		pinnedColumns: computed(() =>
			Array.from(new Set(pins.value.map((pin) => pin.column))),
		),
		/** the crumbs, in reading order. The last one is where the reader is. */
		crumbs,

		push: (entry: DrillEntry) => {
			entries.value = [...entries.value, entry]
		},
		/** the reader asking for the level they are on at another grain */
		regrain,
		/** Pop to `depth` levels. Deeper answers are kept — the reader may return. */
		popTo: (depth: number) => {
			entries.value = entries.value.slice(0, Math.max(0, depth))
		},
		pop: () => {
			entries.value = entries.value.slice(0, -1)
		},

		/** What the server already answered for where the reader now stands. */
		answer: (): DrillLevelData | undefined => answers.get(signature()),
		/**
		 * File an answer under the level it answers, and write its grain back onto
		 * the level first. A click on one of these buckets pins the bucket's first
		 * moment, and only the grain says how far the bucket runs.
		 */
		remember: (answer: DrillLevelData) => {
			if (answer.granularity) regrain(answer.granularity)
			answers.set(signature(), answer)
		},
	})
}

export type DrillStack = ReturnType<typeof makeDrillStack>
