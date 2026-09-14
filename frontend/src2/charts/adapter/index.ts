/**
 * The adapter: the one place a Chart's stored config becomes chart props.
 *
 * The seam it sits on — Insights configures, frappe-ui draws — is settled in
 * `docs/adr/charts-render-through-frappe-ui.md`: the three fillers, the purity
 * rule, and `echartOptions` as the only escape hatch. Read it first.
 *
 * `adaptChart` returns the filler the chart card mounts inside frappe-ui's
 * chrome:
 *
 *     { component, props, drillDown? }
 *
 * `undefined` means there is nothing to draw: a slot is unfilled, or the result
 * carries no column the config asks for. The card shows its unconfigured state.
 *
 * ## Writing one
 *
 * One function per chart type, taking `ChartAdapterInput` and returning a
 * `ChartFiller`, named in `ADAPTERS` below. Read `frappe-ui/src/charts/types.ts`
 * for the props your component takes. Two rules the ADR does not state:
 *
 * - **Two inputs, not one.** With a `split_by` the value columns are named after
 *   the split's values, which the config cannot supply — only the result can.
 * - **One spelling per idea.** Where v2 has a concept, map onto it rather than
 *   keeping an Insights word beside it. `tooltip.measures` is `tooltipColumns`.
 *
 * The one break in the purity rule is the sort a table hands back: it writes the
 * column it was handed, because the sort is a question for the server and the
 * config is what asks it. An adapter that wants a second one is a design change.
 *
 * ## Drill
 *
 * A filler that a reader can point at names its click events in `drillDown`,
 * keyed by the event it emits — `select` for every v2 chart, `regionClick` for
 * the Map that Insights draws itself — each turning the payload into the column
 * and row behind the point. `ChartBody` binds them without knowing which is
 * which, so a plot naming its own event needs nothing from the chrome.
 */

import type { ChartType } from '../../types/chart.types'
import { adaptBarChart, adaptLineChart, adaptRowChart } from './axis'
import { adaptBubbleChart } from './bubble'
import { adaptDonutChart } from './donut'
import { adaptFunnelChart } from './funnel'
import { adaptHeatmapChart } from './heatmap'
import { adaptMapChart } from './map'
import { adaptNumberChart } from './number'
import { adaptSankeyChart } from './sankey'
import { adaptTableChart } from './table'
import type { ChartAdapter, ChartAdapterInput, ChartFiller } from './types'

export type {
	ChartAdapter,
	ChartAdapterInput,
	ChartFailure,
	ChartFiller,
	ChartStateProps,
	DrillDownResolvers,
	DrillDownTarget,
} from './types'

const ADAPTERS: Partial<Record<ChartType, ChartAdapter>> = {
	Bar: adaptBarChart,
	Line: adaptLineChart,
	Row: adaptRowChart,
	Number: adaptNumberChart,
	Donut: adaptDonutChart,
	Funnel: adaptFunnelChart,
	Bubble: adaptBubbleChart,
	Sankey: adaptSankeyChart,
	Heatmap: adaptHeatmapChart,
	Map: adaptMapChart,
	Table: adaptTableChart,
}

export function adaptChart(input: ChartAdapterInput): ChartFiller | undefined {
	return ADAPTERS[input.chart_type]?.(input)
}

const OWN_CARDS: ChartType[] = ['Number']

/**
 * Whether the chrome leaves the card surface undrawn. A Number Chart's readings
 * are cards already, and a card inside a card borders a reading twice. It is a
 * property of the type and not of its data, so the chrome can ask before there
 * is a result to adapt.
 *
 * The same answer settles where the states go. A type with no card of its own has
 * nothing to draw a loading skeleton or a failure on, so the chrome draws them
 * over the plot. A type that draws cards draws them inside each card, and takes
 * `ChartStateProps` for it. That is why its filler is built from the config alone
 * — the cards stand before the first result, and stand when none arrives.
 */
export function drawsOwnCards(chart_type: string): boolean {
	return OWN_CARDS.includes(chart_type as ChartType)
}
