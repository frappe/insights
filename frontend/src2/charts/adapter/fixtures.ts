// Test support. A Chart said as intent — "an axis Chart over a date Dimension,
// measuring revenue, split by region" — and turned into whatever the stored
// shape currently is.
//
// Nothing else in the suite writes a config. The config split rewrites this
// file and every assertion beyond it survives, which is the claim the split
// rests on: if a case here cannot be said in the new shape, the split lost
// something.

import type { GranularityType } from '../../helpers/constants'
import type {
	ConditionalColor,
	FormatGroupArgs,
} from '../../query/components/formatting_utils'
import type {
	AxisChartType,
	ChartConfig,
	NumberComparison,
	NumberFormat,
	ReferenceLine,
	Series,
} from '../../types/chart.types'
import type {
	ColumnDataType,
	DataFormat,
	Dimension,
	Measure,
	QueryResult,
	QueryResultColumn,
} from '../../types/query.types'
import type { ChartAdapterInput } from './types'

type DimensionSpec =
	| string
	| { name: string; type?: ColumnDataType; granularity?: GranularityType }

type MeasureSpec =
	| string
	| {
			name: string
			/** Draws as this instead of the chart's own mark, i.e. a combo series. */
			mark?: 'line' | 'bar'
			/** Measured against the second value axis. */
			axis?: 'right'
			color?: string
			hidden?: boolean
			dataLabels?: boolean
			area?: boolean
			smooth?: boolean
			dataPoints?: boolean
	  }

export type AxisChartSpec = {
	type: AxisChartType
	title?: string
	/** The Dimension along the category axis. */
	dimension: DimensionSpec
	measures: MeasureSpec[]
	/**
	 * One series per value of a second Dimension. `into` is what the server sent
	 * back: it ranks the values, collapses the tail into "Others", and pivots,
	 * so the chart never sees more series than these.
	 */
	splitBy?: { dimension: DimensionSpec; into: string[] }
	/** The categories the result came back with. Two, unless a case needs more. */
	categories?: any[]
	/**
	 * What each value column came back with, one reading per category, for a case
	 * that reads the numbers rather than only their column names. Keyed by the
	 * column the server sent — a Measure's name, or a split value. Left out, the
	 * builder fills numbers of its own.
	 */
	readings?: Record<string, (number | string | null)[]>
	/**
	 * Measures that reach the tooltip and nothing else. They ride the same
	 * summarize, so the result carries a value column for each of them.
	 */
	tooltipMeasures?: MeasureSpec[]
	stacked?: boolean
	normalized?: boolean
	overlap?: boolean
	area?: boolean
	smooth?: boolean
	dataLabels?: boolean
	dataPoints?: boolean
	axisLabel?: string
	min?: number
	max?: number
	referenceLines?: ReferenceLine[]
}

export function axisChart(spec: AxisChartSpec): ChartAdapterInput {
	const dimension = toDimension(spec.dimension)
	const split = spec.splitBy ? toDimension(spec.splitBy.dimension) : undefined
	const measures = spec.measures.map(toMeasureSpec)
	const tooltipMeasures = (spec.tooltipMeasures ?? []).map(toMeasureSpec)
	const drawnColumns = valueColumns(measures, spec.splitBy?.into)
	// What the server sends back for the tooltip Measures. A split leaves them
	// out of the pivot, and a name already drawn is one column, not two — the
	// summarize drops it rather than aliasing the same name twice.
	const drawnNames = new Set(measures.map((measure) => measure.name))
	const columns = [
		...drawnColumns,
		...(spec.splitBy
			? []
			: tooltipMeasures
					.map((measure) => measure.name)
					.filter((name) => !drawnNames.has(name))),
	]
	const categories = spec.categories ?? defaultCategories(dimension)

	// Cast once, here. `ChartConfig` is a union of per-type shapes that no single
	// object satisfies, which is the thing the config split sets out to fix.
	const config = {
		x_axis: { dimension },
		y_axis: {
			series: measures.map(toSeries),
			...(spec.stacked ? { stack: true } : {}),
			...(spec.normalized ? { normalize: true } : {}),
			...(spec.overlap ? { overlap: true } : {}),
			...(spec.area ? { show_area: true } : {}),
			...(spec.smooth ? { smooth: true } : {}),
			...(spec.dataLabels ? { show_data_labels: true } : {}),
			...(spec.dataPoints ? { show_data_points: true } : {}),
			...(spec.axisLabel ? { show_axis_label: true, axis_label: spec.axisLabel } : {}),
			...(spec.min !== undefined ? { min: spec.min } : {}),
			...(spec.max !== undefined ? { max: spec.max } : {}),
			...(spec.referenceLines ? { reference_lines: spec.referenceLines } : {}),
		},
		...(split ? { split_by: { dimension: split } } : {}),
		...(tooltipMeasures.length
			? { tooltip: { measures: tooltipMeasures.map((m) => toSeries(m).measure) } }
			: {}),
	} as unknown as ChartConfig

	return {
		chart_type: spec.type,
		title: spec.title,
		config,
		result: resultOf(dimension, categories, columns, spec.readings),
	}
}

/** The value columns the server sends back, named the way it names them. */
function valueColumns(measures: MeasureSpecObject[], into?: string[]): string[] {
	if (!into) return measures.map((measure) => measure.name)
	// A lone Measure leaves the split values standing on their own. Several of
	// them need the Measure's name beside each value to stay apart. The Measure
	// leads, because `pivot_wider` names a column `values_from` first.
	if (measures.length === 1) return into
	return measures.flatMap((measure) =>
		into.map((value) => `${measure.name}___${value}`),
	)
}

function resultOf(
	dimension: Dimension,
	categories: any[],
	columns: string[],
	readings?: AxisChartSpec['readings'],
): QueryResult {
	const resultColumns: QueryResultColumn[] = [
		{ name: dimension.dimension_name, type: dimension.data_type },
		...columns.map((name): QueryResultColumn => ({ name, type: 'Decimal' })),
	]
	const rows = categories.map((category, index) => {
		const row: Record<string, any> = { [dimension.dimension_name]: category }
		columns.forEach((name, column) => {
			const reading = readings?.[name]?.[index]
			row[name] = reading === undefined ? (index + 1) * 10 + column : reading
		})
		return row
	})

	return resultWith(resultColumns, rows)
}

/** The envelope the query store hands every chart, around the rows it ran. */
function resultWith(
	columns: QueryResultColumn[],
	rows: Record<string, any>[],
): QueryResult {
	return {
		executedSQL: '',
		totalRowCount: rows.length,
		rows,
		// A parallel array, the way the query store builds it: the drill-down
		// reads the row out of it at the same index.
		formattedRows: rows.map((row) => ({ ...row })),
		columns,
		columnOptions: [],
		timeTaken: 0,
		lastExecutedAt: new Date('2026-01-01T00:00:00Z'),
	}
}

type MeasureSpecObject = Exclude<MeasureSpec, string>

function toMeasureSpec(measure: MeasureSpec): MeasureSpecObject {
	return typeof measure === 'string' ? { name: measure } : measure
}

function toSeries(measure: MeasureSpecObject): Series {
	return {
		measure: {
			measure_name: measure.name,
			column_name: measure.name,
			data_type: 'Decimal',
			aggregation: 'sum',
		} as Measure,
		...(measure.mark ? { type: measure.mark } : {}),
		...(measure.axis === 'right' ? { align: 'Right' as const } : {}),
		...(measure.color ? { color: [measure.color] } : {}),
		...(measure.hidden ? { hide_from_chart: true } : {}),
		...(measure.dataLabels ? { show_data_labels: true } : {}),
		...(measure.area ? { show_area: true } : {}),
		...(measure.smooth ? { smooth: true } : {}),
		...(measure.dataPoints ? { show_data_points: true } : {}),
	}
}

function toDimension(dimension: DimensionSpec): Dimension {
	const spec = typeof dimension === 'string' ? { name: dimension } : dimension
	return {
		dimension_name: spec.name,
		column_name: spec.name,
		data_type: (('type' in spec && spec.type) || 'String') as Dimension['data_type'],
		...('granularity' in spec && spec.granularity
			? { granularity: spec.granularity }
			: {}),
	}
}

function defaultCategories(dimension: Dimension) {
	if (dimension.data_type === 'Date' || dimension.data_type === 'Datetime') {
		return ['2026-01-01', '2026-02-01']
	}
	if (dimension.data_type === ('Integer' as Dimension['data_type'])) return [1, 2]
	return ['North', 'South']
}

// The types that draw one picture out of one shape. Each spec says what the
// Chart measures and what came back for it. The server has already grouped and
// ordered every one of these results, so a fixture writes the rows as the
// picture reads them.

export type DonutChartSpec = {
	title?: string
	/** The Dimension the slices are named after. */
	category: DimensionSpec
	measure: string
	/** The slices as the server sent them: biggest first. */
	slices?: { label: any; value: number }[]
	maxSlices?: number
	inlineLabels?: boolean
	legendPosition?: 'top' | 'bottom' | 'left' | 'right'
}

export function donutChart(spec: DonutChartSpec): ChartAdapterInput {
	const label_column = toDimension(spec.category)
	const value_column = toMeasure(spec.measure)
	const slices = spec.slices ?? [
		{ label: 'North', value: 30 },
		{ label: 'South', value: 20 },
	]

	const config = {
		label_column,
		value_column,
		...(spec.maxSlices !== undefined ? { max_slices: spec.maxSlices } : {}),
		...(spec.inlineLabels ? { show_inline_labels: true } : {}),
		...(spec.legendPosition ? { legend_position: spec.legendPosition } : {}),
	} as unknown as ChartConfig

	return {
		chart_type: 'Donut',
		title: spec.title,
		config,
		result: resultWith(
			[columnOfDimension(label_column), columnOfMeasure(value_column)],
			slices.map((slice) => ({
				[label_column.dimension_name]: slice.label,
				[value_column.measure_name]: slice.value,
			})),
		),
	}
}

export type FunnelStageSpec = { stage: string; value: number }

export type FunnelChartSpec = {
	title?: string
	/**
	 * Grouped mode: the Dimension the stages are named after, the Measure read
	 * for each of them, and the row each stage came back on.
	 */
	dimension?: DimensionSpec
	measure?: string
	stages?: FunnelStageSpec[]
	/**
	 * Measures mode: one Measure per stage, aggregated with no group-by, so they
	 * all arrive on one row. The config admits both shapes at once, and the
	 * server derives the Chart from this one whenever it is set.
	 */
	measures?: FunnelStageSpec[]
	/** How every stage prints. One funnel is one scale, so there is no per-stage one. */
	numberFormat?: NumberFormat
	showPercentage?: boolean
}

export function funnelChart(spec: FunnelChartSpec): ChartAdapterInput {
	const label_column = spec.dimension !== undefined ? toDimension(spec.dimension) : undefined
	const value_column = spec.measure !== undefined ? toMeasure(spec.measure) : undefined
	const measures = (spec.measures || []).map((stage) => toMeasure(stage.stage))
	const stages = spec.stages || []

	const config = {
		...(label_column ? { label_column } : {}),
		...(value_column ? { value_column } : {}),
		...(measures.length ? { measures } : {}),
		...(spec.numberFormat ? { number_format: spec.numberFormat } : {}),
		...(spec.showPercentage !== undefined ? { show_percentage: spec.showPercentage } : {}),
	} as unknown as ChartConfig

	const result = spec.measures
		? resultWith(measures.map(columnOfMeasure), [
				Object.fromEntries(spec.measures.map((stage) => [stage.stage, stage.value])),
		  ])
		: resultWith(
				[
					...(label_column ? [columnOfDimension(label_column)] : []),
					...(value_column ? [columnOfMeasure(value_column)] : []),
				],
				stages.map((stage) => ({
					...(label_column ? { [label_column.dimension_name]: stage.stage } : {}),
					...(value_column ? { [value_column.measure_name]: stage.value } : {}),
				})),
		  )

	return { chart_type: 'Funnel', title: spec.title, config, result }
}

export type BubblePointSpec = {
	x: number
	y: number
	size?: number
	/** The point's own name. */
	label?: string
	/** Which group the point belongs to, i.e. what it is colored by. */
	group?: string
}

export type BubbleChartSpec = {
	title?: string
	/** The Measures read against each other. */
	x: string
	y: string
	/** The Measure each point is sized by. */
	size?: string
	/** The Dimension each point is named after. */
	label?: DimensionSpec
	/** The Dimension the points are grouped and colored by. */
	group?: DimensionSpec
	points?: BubblePointSpec[]
	dataLabels?: boolean
	/**
	 * The dividers that cut the plot into quadrants. `shown: false` keeps the
	 * values on the Chart without drawing them.
	 */
	quadrants?: { x?: number; y?: number; shown?: boolean }
}

export function bubbleChart(spec: BubbleChartSpec): ChartAdapterInput {
	const xAxis = toMeasure(spec.x)
	const yAxis = toMeasure(spec.y)
	const size_column = spec.size ? toMeasure(spec.size) : undefined
	const dimension = spec.label ? toDimension(spec.label) : undefined
	const quadrant_column = spec.group ? toDimension(spec.group) : undefined
	const points = spec.points ?? [
		{ x: 10, y: 20 },
		{ x: 30, y: 40 },
	]
	const quadrants = spec.quadrants

	const config = {
		xAxis,
		yAxis,
		...(size_column ? { size_column } : {}),
		...(dimension ? { dimension } : {}),
		...(quadrant_column ? { quadrant_column } : {}),
		...(spec.dataLabels ? { show_data_labels: true } : {}),
		...(quadrants ? { show_quadrants: quadrants.shown ?? true } : {}),
		...(quadrants?.x !== undefined ? { xAxis_refLine: quadrants.x } : {}),
		...(quadrants?.y !== undefined ? { yAxis_refLine: quadrants.y } : {}),
	} as unknown as ChartConfig

	const columns = [
		...(dimension ? [columnOfDimension(dimension)] : []),
		...(quadrant_column ? [columnOfDimension(quadrant_column)] : []),
		columnOfMeasure(xAxis),
		columnOfMeasure(yAxis),
		...(size_column ? [columnOfMeasure(size_column)] : []),
	]

	return {
		chart_type: 'Bubble',
		title: spec.title,
		config,
		result: resultWith(
			columns,
			points.map((point) => ({
				...(dimension ? { [dimension.dimension_name]: point.label } : {}),
				...(quadrant_column ? { [quadrant_column.dimension_name]: point.group } : {}),
				[xAxis.measure_name]: point.x,
				[yAxis.measure_name]: point.y,
				...(size_column ? { [size_column.measure_name]: point.size } : {}),
			})),
		),
	}
}

export type SankeyFlowSpec = { source: string; target: string; value: number }

export type SankeyChartSpec = {
	title?: string
	/** The Dimensions a flow leaves and arrives at. */
	source: DimensionSpec
	target: DimensionSpec
	measure: string
	/** One row per flow, the way the server groups them. */
	flows?: SankeyFlowSpec[]
	orient?: 'horizontal' | 'vertical'
	nodeAlign?: 'left' | 'right' | 'justify'
}

export function sankeyChart(spec: SankeyChartSpec): ChartAdapterInput {
	const source_column = toDimension(spec.source)
	const target_column = toDimension(spec.target)
	const value_column = toMeasure(spec.measure)
	const flows = spec.flows ?? [
		{ source: 'Search', target: 'Tops', value: 30 },
		{ source: 'Email', target: 'Tops', value: 20 },
	]

	const config = {
		source_column,
		target_column,
		value_column,
		...(spec.orient ? { orient: spec.orient } : {}),
		...(spec.nodeAlign ? { node_align: spec.nodeAlign } : {}),
	} as unknown as ChartConfig

	return {
		chart_type: 'Sankey',
		title: spec.title,
		config,
		result: resultWith(
			[
				columnOfDimension(source_column),
				columnOfDimension(target_column),
				columnOfMeasure(value_column),
			],
			flows.map((flow) => ({
				[source_column.dimension_name]: flow.source,
				[target_column.dimension_name]: flow.target,
				[value_column.measure_name]: flow.value,
			})),
		),
	}
}

export type HeatmapCellSpec = { x: string; y: string; value: number }

export type HeatmapChartSpec = {
	title?: string
	/** The Dimensions the grid is cut by: one along the bottom, one up the side. */
	x: DimensionSpec
	y: DimensionSpec
	measure: string
	/** One row per cell, the way the server groups them. */
	cells?: HeatmapCellSpec[]
	showValues?: boolean
	palette?: 'sequential' | 'diverging'
	min?: number
	max?: number
}

export function heatmapChart(spec: HeatmapChartSpec): ChartAdapterInput {
	const x_column = toDimension(spec.x)
	const y_column = toDimension(spec.y)
	const value_column = toMeasure(spec.measure)
	const cells = spec.cells ?? [
		{ x: 'Mon', y: 'Morning', value: 30 },
		{ x: 'Mon', y: 'Evening', value: 12 },
		{ x: 'Tue', y: 'Morning', value: 41 },
	]

	const config = {
		x_column,
		y_column,
		value_column,
		...(spec.showValues ? { show_values: true } : {}),
		...(spec.palette ? { palette: spec.palette } : {}),
		...(spec.min !== undefined ? { min: spec.min } : {}),
		...(spec.max !== undefined ? { max: spec.max } : {}),
	} as unknown as ChartConfig

	return {
		chart_type: 'Heatmap',
		title: spec.title,
		config,
		result: resultWith(
			[
				columnOfDimension(x_column),
				columnOfDimension(y_column),
				columnOfMeasure(value_column),
			],
			cells.map((cell) => ({
				[x_column.dimension_name]: cell.x,
				[y_column.dimension_name]: cell.y,
				[value_column.measure_name]: cell.value,
			})),
		),
	}
}

export type NumberValueSpec = {
	name: string
	/** One reading per period, oldest first, the way the summarize returns them. */
	readings: (number | null)[]
	/** A Measure holding a fraction, which reads as a rate. */
	percent?: boolean
	prefix?: string
	suffix?: string
	decimal?: number
	shorten?: boolean
	color?: string
	/** A metric where a fall is the good news, e.g. churn. */
	negativeIsBetter?: boolean
	/** A fixed number the reading aims at. */
	targetValue?: number
	/** Aims the reading at the `<name>_target` column `target` fills. */
	targetColumn?: boolean
	/** The one number the reading is compared with. Absent falls back to `comparison`. */
	comparison?: NumberComparison
	/** The target column's data, one number per period. */
	target?: (number | null)[]
	/** The reference list a release before `target`/`comparison` wrote. */
	references?: Record<string, any>[]
}

export type NumberChartSpec = {
	title?: string
	values: NumberValueSpec[]
	/** The Dimension the readings are grouped by. A comparison and a sparkline both need one. */
	period?: DimensionSpec
	comparison?: boolean
	sparkline?: boolean
	sparklineColor?: string
	/**
	 * The second run a windowed card's sparkline is drawn from: one reading per
	 * period inside the window, keyed by value name.
	 */
	sparklineSeries?: Record<string, (number | null)[]>
	/** A metric where a fall is the good news, e.g. churn. */
	negativeIsBetter?: boolean
	/** What the Chart sets for every value that sets nothing of its own. */
	prefix?: string
	suffix?: string
	decimal?: number
	shorten?: boolean
}

export function numberChart(spec: NumberChartSpec): ChartAdapterInput {
	const period = spec.period ? toDimension(spec.period) : undefined
	const number_columns = spec.values.map((value) =>
		toMeasure(value.name, value.percent ? 'percent' : undefined),
	)

	const config = {
		number_columns,
		number_column_options: spec.values.map((value) => ({
			...(value.prefix !== undefined ? { prefix: value.prefix } : {}),
			...(value.suffix !== undefined ? { suffix: value.suffix } : {}),
			...(value.decimal !== undefined ? { decimal: value.decimal } : {}),
			...(value.shorten !== undefined ? { shorten_numbers: value.shorten } : {}),
			...(value.color ? { color: value.color } : {}),
			...(value.negativeIsBetter ? { negative_is_better: true } : {}),
			...(value.targetValue !== undefined ? { target: { value: value.targetValue } } : {}),
			...(value.targetColumn ? { target: { measure: toMeasure(`${value.name}_target`) } } : {}),
			...(value.comparison ? { comparison: value.comparison } : {}),
			...(value.references ? { references: value.references } : {}),
		})),
		comparison: Boolean(spec.comparison),
		sparkline: Boolean(spec.sparkline),
		...(spec.sparklineColor ? { sparkline_color: spec.sparklineColor } : {}),
		...(period ? { date_column: period } : {}),
		...(spec.negativeIsBetter ? { negative_is_better: true } : {}),
		...(spec.prefix !== undefined ? { prefix: spec.prefix } : {}),
		...(spec.suffix !== undefined ? { suffix: spec.suffix } : {}),
		...(spec.decimal !== undefined ? { decimal: spec.decimal } : {}),
		...(spec.shorten !== undefined ? { shorten_numbers: spec.shorten } : {}),
	} as unknown as ChartConfig

	const periods = Math.max(...spec.values.map((value) => value.readings.length), 1)
	const rows = Array.from({ length: periods }, (_, index) => ({
		...(period ? { [period.dimension_name]: `2026-${String(index + 1).padStart(2, '0')}-01` } : {}),
		...Object.fromEntries(
			spec.values.flatMap((value) => [
				[value.name, value.readings[index] ?? null],
				...(value.target ? [[`${value.name}_target`, value.target[index] ?? null]] : []),
			]),
		),
	}))

	return {
		chart_type: 'Number',
		title: spec.title,
		config,
		result: resultWith(
			[
				...(period ? [columnOfDimension(period)] : []),
				...number_columns.map(columnOfMeasure),
				...spec.values
					.filter((value) => value.target)
					.map((value) => columnOfMeasure(toMeasure(`${value.name}_target`))),
			],
			rows,
		),
		...(spec.sparklineSeries
			? { sparklineResult: sparklineResultOf(spec.sparklineSeries, period) }
			: {}),
	}
}

/** The second run, as the server returns it: the readings, oldest first. */
function sparklineResultOf(
	series: Record<string, (number | null)[]>,
	period?: Dimension,
): QueryResult {
	const names = Object.keys(series)
	const periods = Math.max(...names.map((name) => series[name].length), 1)
	const rows = Array.from({ length: periods }, (_, index) => ({
		...(period ? { [period.dimension_name]: `2026-01-${String(index + 1).padStart(2, '0')}` } : {}),
		...Object.fromEntries(names.map((name) => [name, series[name][index] ?? null])),
	}))

	return resultWith(
		[
			...(period ? [columnOfDimension(period)] : []),
			...names.map((name) => columnOfMeasure(toMeasure(name))),
		],
		rows,
	)
}

export type MapChartSpec = {
	title?: string
	/** One row per region, spelled the way the data spells it. */
	regions: { region: any; value: number }[]
	measure?: string
	location?: DimensionSpec
	mapType?: 'world' | 'india'
	/** The data's spelling of a region onto the geography's, as an author fixes it. */
	regionMappings?: Record<string, string>
}

export function mapChart(spec: MapChartSpec): ChartAdapterInput {
	const location_column = toDimension(spec.location ?? 'country')
	const value_column = toMeasure(spec.measure ?? 'revenue')
	const map_type = spec.mapType ?? 'world'

	const config = {
		location_column,
		value_column,
		map_type,
		...(spec.regionMappings
			? { region_mappings: { [map_type]: spec.regionMappings } }
			: {}),
	} as unknown as ChartConfig

	return {
		chart_type: 'Map',
		title: spec.title,
		config,
		result: resultWith(
			[columnOfDimension(location_column), columnOfMeasure(value_column)],
			spec.regions.map((region) => ({
				[location_column.dimension_name]: region.region,
				[value_column.measure_name]: region.value,
			})),
		),
	}
}

export type TableMeasureSpec = string | { name: string; format?: DataFormat }

export type TableChartSpec = {
	title?: string
	/** The Dimensions each row is grouped by. They head the row. */
	rows?: DimensionSpec[]
	/**
	 * The Dimension the values are pivoted across, and the columns the server
	 * sent back for it — the pivot happens there, so the table only reads it.
	 */
	pivot?: { dimension: DimensionSpec; into: string[] }
	values: TableMeasureSpec[]
	/** The values of the first row Dimension, one per row. */
	categories?: any[]
	/** The order the Chart itself asks for, which the sort arrows are read off. */
	sortedBy?: { column: string; direction: 'asc' | 'desc' }[]
	filterRow?: boolean
	rowTotals?: boolean
	columnTotals?: boolean
	/** What a release before `number_format` called shortening. Read as an alias. */
	compactNumbers?: boolean
	/** How every value prints, and how one of them overrides that. */
	numberFormat?: NumberFormat
	numberFormats?: Record<string, NumberFormat>
	colorScale?: boolean
	/** A cell rule the author set, e.g. red wherever revenue falls under target. */
	highlight?: { column: string; below: number; color: ConditionalColor }
	stickyColumns?: string[]
	columnWidths?: Record<string, number>
	textWrap?: Record<string, boolean>
}

export function tableChart(spec: TableChartSpec): ChartAdapterInput {
	const rows = (spec.rows ?? ['region']).map(toDimension)
	const pivot = spec.pivot ? toDimension(spec.pivot.dimension) : undefined
	const values = spec.values.map(toTableMeasure)
	const valueNames = valueColumns(
		values.map((measure) => ({ name: measure.measure_name })),
		spec.pivot?.into,
	)
	const categories = spec.categories ?? defaultCategories(rows[0])

	const config = {
		rows,
		columns: pivot ? [pivot] : [],
		values,
		order_by: (spec.sortedBy || []).map((order) => ({
			column: { type: 'column', column_name: order.column },
			direction: order.direction,
		})),
		...(spec.filterRow ? { show_filter_row: true } : {}),
		...(spec.rowTotals ? { show_row_totals: true } : {}),
		...(spec.columnTotals ? { show_column_totals: true } : {}),
		...(spec.compactNumbers ? { compact_numbers: true } : {}),
		...(spec.numberFormat ? { number_format: spec.numberFormat } : {}),
		...(spec.numberFormats ? { number_formats: spec.numberFormats } : {}),
		...(spec.colorScale ? { enable_color_scale: true } : {}),
		...(spec.highlight ? { conditional_formatting: cellRule(spec.highlight) } : {}),
		...(spec.stickyColumns ? { sticky_columns: spec.stickyColumns } : {}),
		...(spec.columnWidths ? { column_widths: spec.columnWidths } : {}),
		...(spec.textWrap ? { text_wrap: spec.textWrap } : {}),
	} as unknown as ChartConfig

	const resultColumns: QueryResultColumn[] = [
		...rows.map(columnOfDimension),
		...valueNames.map((name): QueryResultColumn => ({ name, type: 'Decimal' })),
	]
	const resultRows = categories.map((category, index) => {
		const row: Record<string, any> = {}
		rows.forEach((dimension, position) => {
			row[dimension.dimension_name] = position === 0 ? category : `${category} ${position}`
		})
		valueNames.forEach((name, position) => {
			row[name] = (index + 1) * 10 + position
		})
		return row
	})

	return {
		chart_type: 'Table',
		title: spec.title,
		config,
		result: resultWith(resultColumns, resultRows),
	}
}

function cellRule(highlight: NonNullable<TableChartSpec['highlight']>): FormatGroupArgs {
	const target = { type: 'column' as const, column_name: highlight.column }
	return {
		formats: [
			{
				mode: 'cell_rules',
				column: target,
				operator: '<',
				value: highlight.below,
				color: highlight.color,
			},
		],
		columns: [target],
	}
}

function toTableMeasure(measure: TableMeasureSpec): Measure {
	if (typeof measure === 'string') return toMeasure(measure)
	return toMeasure(measure.name, measure.format)
}

function toMeasure(name: string, format?: 'currency' | 'percent'): Measure {
	return {
		measure_name: name,
		column_name: name,
		data_type: 'Decimal',
		aggregation: 'sum',
		...(format ? { format } : {}),
	} as Measure
}

const columnOfDimension = (dimension: Dimension): QueryResultColumn => ({
	name: dimension.dimension_name,
	type: dimension.data_type,
})

const columnOfMeasure = (measure: Measure): QueryResultColumn => ({
	name: measure.measure_name,
	type: measure.data_type,
})
