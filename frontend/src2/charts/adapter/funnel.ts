import { FunnelChart } from 'frappe-ui/charts'
import type { FunnelChartProps, FunnelStageEvent } from 'frappe-ui/charts'
import type { FunnelChartConfig } from '../../types/chart.types'
import type { Measure, QueryResultRow } from '../../types/query.types'
import { numberFormatter } from '../number_format'
import type { ChartAdapterInput, ChartFiller } from './types'

// A funnel is stored in two shapes and v2 reads one: a stage column and a value
// column, one row per stage. The grouped shape is already that. The Measures
// shape is one row carrying every stage side by side, so Insights turns it on
// its side here — v2 takes data as it is drawn, and reshaping it is the
// caller's.
//
// The columns of the reshaped rows are named here because the rows are built
// here. They name nothing in the result.
const STAGE = 'stage'
const VALUE = 'value'

export function adaptFunnelChart(input: ChartAdapterInput): ChartFiller | undefined {
	const config = input.config as FunnelChartConfig
	const measures = (config.measures || []).filter((measure) => measure.measure_name)
	return measures.length ? measuresFunnel(input, config, measures) : groupedFunnel(input, config)
}

/** One row per stage: the shape a group-by produces, and the shape v2 reads. */
function groupedFunnel(
	input: ChartAdapterInput,
	config: FunnelChartConfig,
): ChartFiller | undefined {
	const category = config.label_column?.dimension_name
	const value = config.value_column?.measure_name
	if (!category || !value) return

	return {
		component: FunnelChart,
		props: funnelProps(input, config, input.result.rows, category, value, config.value_column),
		drillDown: {
			select: (event: FunnelStageEvent) => ({ column: value, row: event.row }),
		},
	}
}

/** Several Measures on one row, each one a stage, turned into one row each. */
function measuresFunnel(
	input: ChartAdapterInput,
	config: FunnelChartConfig,
	measures: Measure[],
): ChartFiller | undefined {
	const row = input.result.rows[0]
	if (!row) return

	// A stage the query returned nothing for is not a stage of zero: `|| 0` drew a
	// missing count as a real one, and a funnel reads its stages against each
	// other. The heatmap states the same rule in its own header.
	const data = measures.map((measure) => {
		const raw = row[measure.measure_name]
		const value = Number(raw)
		return {
			[STAGE]: measure.measure_name,
			[VALUE]: raw === null || raw === undefined || !Number.isFinite(value) ? null : value,
		}
	})

	return {
		component: FunnelChart,
		// Every stage is a Measure of its own, and a funnel prints one scale, so
		// the first stage says how all of them read. They are the same quantity
		// counted at different points — a funnel whose stages disagree on their
		// unit is not a funnel.
		props: funnelProps(input, config, data, STAGE, VALUE, measures[0]),
		drillDown: {
			// The stage label is the Measure's name, which is what the result calls
			// the column behind it. The row is the one row every stage was read off.
			select: (event: FunnelStageEvent) => ({ column: event.label, row }),
		},
	}
}

function funnelProps(
	input: ChartAdapterInput,
	config: FunnelChartConfig,
	data: QueryResultRow[],
	category: string,
	value: string,
	measure?: Measure,
): FunnelChartProps {
	const props: FunnelChartProps = {
		title: input.title,
		data,
		category,
		value,
		format: numberFormatter(config, measure, input.result.rows),
	}
	return props
}
