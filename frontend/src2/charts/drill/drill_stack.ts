// The drill stack: what a segment click means, what the reader has drilled
// through, and what has already come back for it.
//
// Everything here is a function of plain values — a Chart's config, the raw row
// a click reported, the levels pushed so far. No network and no component: the
// stack holds refs so a dialog can render it, and that is the whole of its
// reach into Vue. The dialog above is a rendering concern — it pushes, it pops,
// it reads the trail, and it asks `drill_api` for what the cache has not got.
//
// The one model, for every chart type: a click reduces to a set of **segment
// filters** — the dimension values it pins, as (column, operator, literal)
// triples against the query's pre-summarize surface. A number card pins the
// empty set. Nothing past `segmentOf` knows which type was clicked.

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
 * What a level does with its segment.
 *
 * Both carry the Measure the click landed on. A breakdown re-measures the number
 * the reader pointed at rather than the Chart's first one — and a records level
 * needs it too, because a Measure can carry a condition of its own ("count the
 * overdue ones"), and rows that ignored it would not add up to the number that
 * was clicked.
 *
 * `granularity` is what the reader asked a date breakdown for. Left off, the
 * server picks the grain the segment's span deserves; said, it wins. So the
 * absent field is not "no grain" — it is "you choose", and the answer says which.
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

/** What a segment click pins, before the reader has said what to do with it. */
export type DrillSegment = {
	/** The pins, as the wire carries them. Empty for a number card. */
	filters: DrillFilter[]
	/** Pre-summarize columns this segment pins — subtracted from the candidates. */
	pins: string[]
	/** The pinned values, for the crumb. Empty when nothing is pinned. */
	label: string
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
 * A query builder's own result, read as a Chart.
 *
 * The query builder has no Chart — it has the pipeline it is editing — but the
 * step that aggregated its rows says the same thing a Chart's config does: which
 * columns a click pins, and which numbers it can land on. So the aggregating
 * step is read straight into a Table config, and every other reader of a
 * `DrillChart` works unchanged.
 *
 * This is not the retired client-side derivation coming back. Nothing is sliced
 * and nothing is sent: the server is still told the whole pipeline and still
 * decides where to cut it. Undefined when nothing aggregated, which is a result
 * with nothing behind it.
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
	const pins: string[] = []
	const labels: string[] = []

	for (const dimension of declared.rows) {
		const value = target.row?.[dimension.dimension_name]
		filters.push(filterForDimension(dimension, value))
		pins.push(dimension.column_name)
		labels.push(labelForDimension(dimension, value))
	}

	declared.columns.forEach((dimension, index) => {
		const value = pivot.values[index]
		if (value === undefined) return
		filters.push(filterForDimension(dimension, value))
		pins.push(dimension.column_name)
		labels.push(labelForDimension(dimension, value))
	})

	return { filters, pins, label: labels.join(' · '), measure: pivot.measure }
}

/**
 * The grain a records level's date columns are printed at.
 *
 * A records level groups nothing, so its dates carry no grain of their own —
 * and printed raw they read as machine output. The column's own type is the
 * honest grain there: a `Date` is a day, a `Datetime` is a moment. A grouped
 * date is a different reading: the answer names the one grain it grouped by,
 * and the chart drawing it is told directly.
 */
export function drillGranularity(columns: QueryResultColumn[]): Record<string, string> {
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
 * carried, less every column the path has pinned — this click's, and the ones
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

/** One level, plus the two things only the reader needs: its crumbs. */
export type DrillEntry = {
	level: DrillLevel
	/** the segment the reader clicked to get here. Empty when it pins nothing. */
	segmentLabel: string
	/** what this level does — "by Region", "Records" */
	actionLabel: string
}

/**
 * One crumb of the trail. `depth` is the stack this crumb stands for, so
 * clicking it pops to exactly that many levels. Both of a level's crumbs carry
 * the same depth: "Overdue › by Region" is one level read as two words.
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
	 * Whether the Dimension this level broke down has an order of its own. A date
	 * does; a status does not. It decides the whole reading: an ordered level came
	 * back in that order, cut to the most recent stretch, and a ranked one came
	 * back biggest first. The server answers it — no client sniffs a column type
	 * to guess at it, because the cut and the reading have to agree.
	 */
	ordered?: boolean
	/** the grain an ordered breakdown was grouped by, whoever chose it */
	granularity?: string | null
	/** how many rows there are behind the bounded few that came back */
	total_row_count?: number
	/** only on a records level, and only when the convention held */
	record_link?: { doctype: string; column: string }
	/**
	 * The pipeline the server sliced for this level, and the connection it ran
	 * on. The authoring door alone answers with them — they are what "open as
	 * query" hands to the builder — and a reading surface never sees either.
	 */
	operations?: Operation[]
	use_live_connection?: boolean
}

/**
 * What the dialog drills, as the surface that opened it hands it over: the shape
 * a click is read against, what a breakdown may offer, and the one call that
 * answers a level.
 *
 * Which door `fetch` goes through is the surface's business — a saved chart's
 * name from a reading surface, the config or the pipeline being edited from an
 * authoring one. The dialog cannot tell them apart, and has no reason to: the
 * only difference it ever sees is that an authoring answer carries `operations`.
 */
export type DrillSubject = {
	chart: DrillChart
	/** the head of the breadcrumb trail — what the reader clicked into */
	title: string
	dimensions: DrillDimension[]
	fetch: (levels: DrillLevel[]) => Promise<DrillLevelData>
}

/**
 * The reader's path through one dialog. Push to go deeper, pop to retrace.
 *
 * Pops cost nothing: every level's answer is held against the exact stack that
 * produced it, so retracing never asks the server again. Keying on the stack
 * rather than on the depth is what makes "pop, then drill somewhere else" serve
 * the new level instead of the old one's rows.
 */
export function makeDrillStack() {
	// shallow on purpose: an entry is replaced, never edited, and the rows a
	// level answered with have no business being made reactive one cell at a time
	const entries = shallowRef<DrillEntry[]>([])
	const answers = new Map<string, DrillLevelData>()

	const levels = computed<DrillLevel[]>(() => entries.value.map((entry) => entry.level))
	const signature = () => JSON.stringify(levels.value)

	const crumbs = computed<DrillCrumb[]>(() => {
		const trail: DrillCrumb[] = []
		entries.value.forEach((entry, index) => {
			const depth = index + 1
			if (entry.segmentLabel) trail.push({ label: entry.segmentLabel, depth })
			trail.push({ label: entry.actionLabel, depth })
		})
		return trail
	})

	return reactive({
		entries,
		/** exactly what `get_drill_data` is sent */
		levels,
		depth: computed(() => entries.value.length),
		current: computed(() => entries.value[entries.value.length - 1]),
		/**
		 * Every column the path has fixed. A Dimension already pinned upstream is
		 * not a way of splitting anything further down, so the menu stops offering
		 * it as the reader descends.
		 */
		pinned: computed(() =>
			Array.from(
				new Set(
					entries.value.flatMap((entry) =>
						entry.level.segment_filters.map((filter) => filter.column),
					),
				),
			),
		),
		/** the trail, in reading order. The last crumb is where the reader is. */
		crumbs,

		push: (entry: DrillEntry) => {
			entries.value = [...entries.value, entry]
		},
		/**
		 * The level the reader is standing on, asked for again at a grain they
		 * chose. It replaces the level rather than pushing one: a grain is how this
		 * level reads, not a step below it, so the trail and the way back out are
		 * the same afterwards as before.
		 *
		 * The answer already held is left where it is. It answers the level as it
		 * was asked then, and an answer is filed under the whole path — so a level
		 * whose action has changed simply has none yet, and the dialog fetches.
		 */
		regrain: (granularity: string) => {
			const entry = entries.value[entries.value.length - 1]
			const action = entry?.level.action
			if (!action || !('breakdown' in action)) return

			const regrained = {
				...entry,
				level: { ...entry.level, action: { ...action, granularity } },
			}
			entries.value = [...entries.value.slice(0, -1), regrained]
		},
		/** Pop to `depth` levels. Deeper answers are kept — the reader may return. */
		popTo: (depth: number) => {
			entries.value = entries.value.slice(0, Math.max(0, depth))
		},
		pop: () => {
			entries.value = entries.value.slice(0, -1)
		},

		/** What the server already answered for where the reader now stands. */
		answer: (): DrillLevelData | undefined => answers.get(signature()),
		remember: (data: DrillLevelData) => {
			answers.set(signature(), data)
		},
	})
}

export type DrillStack = ReturnType<typeof makeDrillStack>
