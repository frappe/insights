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
	AxisChartType,
	ChartConfig,
	ReferenceLine,
	Series,
} from '../../types/chart.types'
import type {
	ColumnDataType,
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
	const columns = valueColumns(measures, spec.splitBy?.into)
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
	} as unknown as ChartConfig

	return {
		chart_type: spec.type,
		title: spec.title,
		config,
		result: resultOf(dimension, categories, columns),
	}
}

/** The value columns the server sends back, named the way it names them. */
function valueColumns(measures: MeasureSpecObject[], into?: string[]): string[] {
	if (!into) return measures.map((measure) => measure.name)
	// A lone Measure leaves the split values standing on their own; several of
	// them need the Measure's name beside each value to stay apart.
	if (measures.length === 1) return into
	return into.flatMap((value) =>
		measures.map((measure) => `${value}___${measure.name}`),
	)
}

function resultOf(
	dimension: Dimension,
	categories: any[],
	columns: string[],
): QueryResult {
	const resultColumns: QueryResultColumn[] = [
		{ name: dimension.dimension_name, type: dimension.data_type },
		...columns.map((name): QueryResultColumn => ({ name, type: 'Decimal' })),
	]
	const rows = categories.map((category, index) => {
		const row: Record<string, any> = { [dimension.dimension_name]: category }
		columns.forEach((name, column) => {
			row[name] = (index + 1) * 10 + column
		})
		return row
	})

	return {
		executedSQL: '',
		totalRowCount: rows.length,
		rows,
		// A parallel array, the way the query store builds it: the drill-down
		// reads the row out of it at the same index.
		formattedRows: rows.map((row) => ({ ...row })),
		columns: resultColumns,
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
