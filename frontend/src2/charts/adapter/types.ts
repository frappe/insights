import type { Component } from 'vue'
import type { ChartConfig, ChartType } from '../../types/chart.types'
import type { QueryResult, QueryResultRow } from '../../types/query.types'

// The contract every chart type is adapted against. `index.ts` states it in
// prose; this file states it in types.

export type ChartAdapterInput = {
	chart_type: ChartType
	/** The Chart's stored config, as the type it belongs to reads it. */
	config: ChartConfig
	/** The rows and columns the server ran for it. A split's series live here. */
	result: QueryResult
	/** Printed by the chrome. It belongs to the Chart, not to its config. */
	title?: string
}

/** The point a reader clicked, as a drill-down reads it. */
export type DrillDownTarget = {
	/** Name of the result column the value came from. */
	column: string
	/** The row behind the point, as it stands in `result.rows`. */
	row: QueryResultRow
}

/**
 * Keyed by the event the filler emits, e.g. `datapointClick`. Each entry turns
 * that event's payload into the point behind it, or `undefined` when the click
 * landed on nothing drillable.
 */
export type DrillDownResolvers = Record<
	string,
	// eslint-disable-next-line no-unused-vars
	(event: any) => DrillDownTarget | undefined
>

/** What fills the chart chrome, and everything the card needs to mount it. */
export type ChartFiller = {
	component: Component
	/** `v-bind`-ready. Typed at the point each adapter builds it. */
	props: Record<string, any>
	drillDown?: DrillDownResolvers
}

// eslint-disable-next-line no-unused-vars
export type ChartAdapter = (input: ChartAdapterInput) => ChartFiller | undefined
