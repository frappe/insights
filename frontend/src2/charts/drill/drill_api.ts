// The doors the drill goes through.
//
// Every server call the drill makes is here, so the whole client-side reading of
// the drill endpoints is one file to reconcile if they answer differently from
// what this expects. Nothing above this module knows an endpoint's name, its
// argument names, or the shape of its answer beyond `DrillLevelData`.
//
// The contract, as ticket 11 ratified it:
//
//     viewer.get_drill_data(chart, dashboard?, filters?, drill_stack)
//
// `chart` and `dashboard` are the same references `get_chart_data` takes — they
// name the permission gate and the data authority, and nothing on the wire can
// flip either. `filters` is the dashboard filter state the card was showing, so
// the rows agree with the number that was clicked. `drill_stack` is the
// descriptor: literals and an action per level. No operations cross in either
// direction.
//
// The authoring half is the same walk for a shape nobody has saved:
//
//     authoring.get_drill_data(query, drill_stack, chart_type?, config?, operations?, ...)
//
// It names what it is drilling instead of naming a chart — the config the chart
// builder is editing, or the operations the query builder is. That door is the
// only one that answers with operations, and it is closed to anyone without an
// authoring seat.

import { call } from 'frappe-ui'
import type { ViewerFilters } from '../../dashboard/viewer'
import type { ChartConfig } from '../../types/chart.types'
import type { Operation } from '../../types/query.types'
import type { DashboardFilterContext } from '../chart_read'
import type { DrillDimension, DrillLevel, DrillLevelData } from './drill_stack'

export type DrillRequest = {
	chart: string
	dashboard?: string
	filters?: ViewerFilters
	drill_stack: DrillLevel[]
}

export function fetchDrillData(request: DrillRequest): Promise<DrillLevelData> {
	return call('insights.api.viewer.get_drill_data', {
		chart: request.chart,
		dashboard: request.dashboard,
		filters: request.filters,
		drill_stack: request.drill_stack,
	})
}

/**
 * What an authoring surface is drilling. Both forms name the source query — it
 * carries the connection and the read check — and then say what shape sits on
 * top of it: the chart being configured, or the pipeline being edited.
 */
export type AuthoringDrillSubject =
	| { query: string; chart_type: string; config: ChartConfig }
	| { query: string; operations: Operation[] }

export function fetchAuthoringDrillData(
	subject: AuthoringDrillSubject,
	drill_stack: DrillLevel[],
	// the grid's filter state, unrouted: which query each filter lands on is read
	// on the server, the same way it is for the preview itself
	filterContext?: DashboardFilterContext,
): Promise<DrillLevelData> {
	return call('insights.api.authoring.get_drill_data', {
		...subject,
		drill_stack,
		chart_name: filterContext?.chart,
		dashboard_items: filterContext?.items,
		filters: filterContext?.filters,
	})
}

export function fetchAuthoringDrillDimensions(
	subject: AuthoringDrillSubject,
): Promise<DrillDimension[]> {
	return call('insights.api.authoring.get_drill_dimensions', subject).then(
		(response) => (response as { dimensions?: DrillDimension[] })?.dimensions || [],
	)
}
