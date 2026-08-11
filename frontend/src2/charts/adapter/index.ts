/**
 * The adapter: the one place a Chart's stored config becomes chart props.
 *
 * Insights configures charts. frappe-ui draws them. Between the two sits this
 * module, and nothing else: no surface builds an option for a type v2 admits,
 * and no surface draws chrome of its own.
 *
 * ## The contract
 *
 * `adaptChart` takes a Chart and returns the **filler** — the one thing the
 * chart card mounts inside its chrome:
 *
 *     { component, props, drillDown? }
 *
 * `ChartBody` mounts it and knows nothing else. It does not switch on chart
 * type, and adding a type must not make it. A type is added here, by writing one
 * function and naming it in `ADAPTERS` below.
 *
 * A filler is one of three things, and the card treats all three alike:
 *
 *   1. a frappe-ui charts v2 component, for every type v2 admits;
 *   2. an Insights plot built on v2's `useChart`, for Map, whose geography layer
 *      v2's scope rule keeps out of the library;
 *   3. no plot at all, for Table: the filler draws the grid, and wears the same
 *      card and the same states as every other type.
 *
 * `undefined` means there is nothing to draw: a slot is unfilled, or the result
 * carries no column the config asks for. The card shows its unconfigured state.
 *
 * ## Writing one
 *
 * One function per chart type, taking `ChartAdapterInput` and returning a
 * `ChartFiller`. Read `frappe-ui/src/charts/types.ts` for the props your
 * component takes; that file and this comment are all you need.
 *
 * Rules the family holds to:
 *
 * - **Pure.** No Vue reactivity, no network, no ECharts. Config and result in,
 *   props out. That is what makes it testable without a browser.
 * - **Two inputs, not one.** With a `split_by` the value columns are named after
 *   the split's values, which the config cannot supply — only the result can.
 * - **One spelling per idea.** Where v2 has a concept, map onto it rather than
 *   keeping an Insights word beside it. `hide_from_chart` is `hiddenSeries`.
 * - **`echartOptions` is the only escape hatch**, and it is for instructions to
 *   the renderer. A default that is wrong for every app is a frappe-ui change.
 *
 * ## Drill-down
 *
 * A filler that a reader can point at names its click events in `drillDown`,
 * keyed by the event it emits — `select` for every v2 chart, `regionClick` for
 * the Map that Insights draws itself — each turning the payload into the column
 * and row behind the point. `ChartBody` binds them without knowing which is
 * which, so a plot naming its own event needs nothing from the chrome. v2's
 * typed events carry the row itself, so nothing maps a datapoint index back onto
 * the result.
 */

import type { ChartType } from '../../types/chart.types'
import { adaptBarChart, adaptLineChart, adaptRowChart } from './axis'
import { adaptBubbleChart } from './bubble'
import { adaptDonutChart } from './donut'
import { adaptFunnelChart } from './funnel'
import { adaptMapChart } from './map'
import { adaptNumberChart } from './number'
import { adaptSankeyChart } from './sankey'
import { adaptTableChart } from './table'
import type { ChartAdapter, ChartAdapterInput, ChartFiller } from './types'

export type {
	ChartAdapter,
	ChartAdapterInput,
	ChartFiller,
	DrillDownResolvers,
	DrillDownTarget,
} from './types'

// Every chart type, and the one function that adapts it.
const ADAPTERS: Partial<Record<ChartType, ChartAdapter>> = {
	Bar: adaptBarChart,
	Line: adaptLineChart,
	Row: adaptRowChart,
	Number: adaptNumberChart,
	Donut: adaptDonutChart,
	Funnel: adaptFunnelChart,
	Bubble: adaptBubbleChart,
	Sankey: adaptSankeyChart,
	Map: adaptMapChart,
	Table: adaptTableChart,
}

export function adaptChart(input: ChartAdapterInput): ChartFiller | undefined {
	return ADAPTERS[input.chart_type]?.(input)
}
