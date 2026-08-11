import { SankeyChart } from 'frappe-ui/charts'
import type { SankeyChartProps, SankeyLinkEvent } from 'frappe-ui/charts'
import type { SankeyChartConfig } from '../../types/chart.types'
import type { ChartAdapterInput, ChartFiller } from './types'

// The server groups a sankey by its source and its target, so the result is
// already one row per flow.

export function adaptSankeyChart(input: ChartAdapterInput): ChartFiller | undefined {
	const config = input.config as SankeyChartConfig
	const source = config.source_column?.dimension_name || config.source_column?.column_name
	const target = config.target_column?.dimension_name || config.target_column?.column_name
	const value = config.value_column?.measure_name
	if (!source || !target || !value) return

	const props: SankeyChartProps = {
		title: input.title,
		data: input.result.rows,
		source,
		target,
		value,
	}
	if (config.orient) props.orient = config.orient
	if (config.node_align) props.nodeAlign = config.node_align

	return {
		component: SankeyChart,
		props,
		drillDown: {
			select: (event: SankeyLinkEvent) => ({ column: value, row: event.row }),
		},
	}
}
