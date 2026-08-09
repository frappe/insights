import { ScatterChart } from 'frappe-ui/charts'
import type {
	ReferenceLine as PlotReferenceLine,
	ScatterChartProps,
	ScatterPointEvent,
} from 'frappe-ui/charts'
import type { BubbleChartConfig } from '../../types/chart.types'
import type { ChartAdapterInput, ChartFiller } from './types'

export function adaptBubbleChart(input: ChartAdapterInput): ChartFiller | undefined {
	const config = input.config as BubbleChartConfig
	const x = config.xAxis?.measure_name
	const y = config.yAxis?.measure_name
	if (!x || !y) return

	const props: ScatterChartProps = {
		title: input.title,
		data: input.result.rows,
		x,
		y,
	}

	const size = config.size_column?.measure_name
	if (size) props.size = size

	// The point's own name, which heads its tooltip. Insights calls it the name
	// column and v2 calls it the label; one idea, so it is not kept under both.
	const label = config.dimension?.dimension_name || config.dimension?.column_name
	if (label) props.label = label

	// The name beside the point, not a measure: both measures are already on the
	// axes. A Chart that asks for labels and names no column is told so by v2.
	if (config.show_data_labels) props.showDataLabels = true

	// Coloring the points by a Dimension is grouping them by it, which is what a
	// series is. The Insights name says what the groups were meant to read as.
	const series = config.quadrant_column?.dimension_name || config.quadrant_column?.column_name
	if (series) props.series = series

	const referenceLines = quadrantLines(config)
	if (referenceLines.length) props.referenceLines = referenceLines

	return {
		component: ScatterChart,
		props,
		drillDown: {
			// A point stands at the crossing of two Measures. It drills into the
			// vertical one, which is the measure a quadrant chart is read down.
			pointClick: (event: ScatterPointEvent) => ({ column: y, row: event.row }),
		},
	}
}

/**
 * Both axes of a scatter are value axes, so a quadrant is drawn by a pair of
 * reference lines and `axis: 'x'` takes a number rather than a category. The
 * numbers are the author's own: nothing computes a default divider, and a
 * quadrant chart with no line set draws none.
 */
function quadrantLines(config: BubbleChartConfig): PlotReferenceLine[] {
	if (!config.show_quadrants) return []
	return [
		{ axis: 'x' as const, value: config.xAxis_refLine },
		{ axis: 'y' as const, value: config.yAxis_refLine },
	]
		.filter((line) => line.value !== undefined && line.value !== null)
		.map((line) => ({ ...line, value: line.value as number, dashed: true }))
}
