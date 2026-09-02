// A breakdown level as a Chart.
//
// Which shape draws a level is read off the answer and nowhere else. The server
// owns the cut — which way the rows run, how many came back, the grain they were
// bucketed at, whether they add up — and the shape has to agree with the cut, so
// a shape guessed from a column type would put two owners on one decision.
//
// The rules, in order:
//
//   nothing numeric to draw      →  Table
//   ordered, few buckets         →  Bar    a line through three points draws a
//                                          trend the three points do not have
//   ordered                      →  Line
//   ranked, parts of one whole   →  Donut
//   ranked                       →  Row
//
// And one rule for labels: a label belongs on a mark you read a value off, not
// on a mark you read a shape off. Bars and slices carry them when they fit. A
// line never does, because a label on every point of a stretch buries the shape.

import { FIELDTYPES, type GranularityType } from '../../helpers/constants'
import type {
	AxisChartConfig,
	ChartConfig,
	ChartType,
	DonutChartConfig,
	TableChartConfig,
} from '../../types/chart.types'
import type {
	Dimension,
	DimensionDataType,
	Measure,
	MeasureDataType,
	QueryResultColumn,
} from '../../types/query.types'
import { columnLabel, type DrillChart, type DrillLevelData } from './drill_stack'

/** What a breakdown level draws itself from: the answer, whole. */
export type BreakdownAnswer = Pick<
	DrillLevelData,
	'columns' | 'rows' | 'ordered' | 'granularity' | 'additive' | 'total_row_count'
>

/** Below this a series has too few readings to trace, and bars read them plainly. */
const FEW_BUCKETS = 4

/** A ring under two slices is a circle, and over six it stops being countable. */
const SLICES = { min: 2, max: 6 }

/** How many marks a plot can label before the labels collide. */
const LABEL_BUDGET = 20

/** The shape an answer draws itself as, and whether its marks carry values. */
export type BreakdownPlot = {
	chart_type: ChartType
	labels: boolean
}

/**
 * The one decision. Everything it reads is on the answer, so the same rules hold
 * for a level clicked out of a dashboard card and one clicked out of the query
 * builder — neither has anything else to offer.
 */
export function breakdownPlot(dimension: string, answer: BreakdownAnswer): BreakdownPlot {
	const values = valueColumns(dimension, answer.columns)
	const fits = answer.rows.length * values.length <= LABEL_BUDGET

	// a measure that came back as text plots as nothing. The grid draws it rather
	// than leaving an empty pane where a chart was expected
	if (!values.length) return { chart_type: 'Table', labels: false }

	if (answer.ordered) {
		const few = answer.rows.length <= FEW_BUCKETS
		return few ? { chart_type: 'Bar', labels: fits } : { chart_type: 'Line', labels: false }
	}

	if (partsOfAWhole(answer, values)) return { chart_type: 'Donut', labels: fits }

	return { chart_type: 'Row', labels: fits }
}

/**
 * Whether this level's groups can be read as parts of one whole.
 *
 * Four things have to hold, and a ring lies if any of them does not: the groups
 * add up, all of them came back rather than the biggest few, none of them is
 * negative, and there are few enough to tell apart. One number per group, too —
 * a ring divides one total, and several measures are several totals.
 */
function partsOfAWhole(answer: BreakdownAnswer, values: QueryResultColumn[]): boolean {
	if (!answer.additive || values.length !== 1) return false

	const shown = answer.rows.length
	if (shown < SLICES.min || shown > SLICES.max) return false
	if ((answer.total_row_count ?? shown) > shown) return false

	const value = values[0].name
	return answer.rows.every((row) => Number(row[value]) >= 0)
}

/**
 * The columns holding the numbers this level drew, in the order the result
 * carries them. A click that named a measure has one, and a click on a number
 * card named none and kept every measure the card drew.
 */
function valueColumns(dimension: string, columns: QueryResultColumn[]): QueryResultColumn[] {
	return columns.filter(
		(column) => column.name !== dimension && FIELDTYPES.NUMBER.includes(column.type),
	)
}

/** The Chart a breakdown level draws itself as. */
export function breakdownChart(dimension: string, answer: BreakdownAnswer): DrillChart {
	const plot = breakdownPlot(dimension, answer)
	const values = valueColumns(dimension, answer.columns).map(measureSlot)
	const column = dimensionSlot(dimension, answer)

	return {
		chart_type: plot.chart_type,
		config: configFor(plot, column, values),
	}
}

function configFor(plot: BreakdownPlot, dimension: Dimension, values: Measure[]): ChartConfig {
	if (plot.chart_type === 'Table') {
		return { rows: [dimension], columns: [], values } as TableChartConfig
	}

	if (plot.chart_type === 'Donut') {
		return {
			label_column: dimension,
			value_column: values[0],
			show_inline_labels: plot.labels,
		} as DonutChartConfig
	}

	const axis: AxisChartConfig = {
		x_axis: { dimension },
		y_axis: {
			series: values.map((measure) => ({ measure })),
			show_data_labels: plot.labels,
			// What the bars measure. The crumb says which Dimension the level cut
			// by and never what it counted, and the axis title is where a chart
			// already answers that — drawn over the plot edge, not as a heading.
			// Several measures have no one name, so they go unnamed here and the
			// legend names each of them.
			...(values.length === 1
				? { show_axis_label: true, axis_label: columnLabel(values[0].measure_name) }
				: {}),
		},
	}
	// `ChartConfig` names Bar and Line separately, and each of them narrows the
	// y-axis to marks of one kind. The adapter reads the family's shared shape,
	// which is this one, and the union has no name for it.
	return axis as unknown as ChartConfig
}

function dimensionSlot(dimension: string, answer: BreakdownAnswer): Dimension {
	const type = answer.columns.find((column) => column.name === dimension)?.type || 'String'

	return {
		dimension_name: dimension,
		column_name: dimension,
		data_type: type as DimensionDataType,
		// what the buckets on the axis stand for. It prints them, and it is also
		// what a click inside the level reads its own crumb at.
		granularity: (answer.granularity || undefined) as GranularityType | undefined,
	}
}

function measureSlot(column: QueryResultColumn): Measure {
	return {
		measure_name: column.name,
		column_name: column.name,
		data_type: column.type as MeasureDataType,
		// The level's own summarize already aggregated these, and the shape reads
		// the numbers as they stand. The slot demands an aggregation and nothing
		// downstream reads it.
		aggregation: 'sum',
	}
}
