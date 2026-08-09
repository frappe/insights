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
	/**
	 * The surface cannot change the Chart. A control that rewrites the config —
	 * a table's sort — is left out rather than drawn dead.
	 */
	readonly?: boolean
	/**
	 * The next run is in flight. Only a filler that keeps its last picture while
	 * it reloads has anything to say about this; the rest are replaced by the
	 * card's loading state before they are asked.
	 */
	executing?: boolean
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
	/**
	 * Whether the chrome draws the card surface around the filler. One plot gets
	 * one card, so `true` is the default. A filler that draws several cards of
	 * its own — a Number Chart's readings — says `false`, or every one of them
	 * sits inside a second border.
	 */
	card?: boolean
}

// eslint-disable-next-line no-unused-vars
export type ChartAdapter = (input: ChartAdapterInput) => ChartFiller | undefined
