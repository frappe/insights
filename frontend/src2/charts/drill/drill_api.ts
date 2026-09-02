// The door the drill goes through.
//
// Every server call the drill makes is here, so the whole client-side reading of
// the drill endpoint is one file to reconcile if it answers differently from
// what this expects. Nothing above this module knows an endpoint's name, its
// argument names, or the shape of its answer beyond `DrillLevelData`.
//
// The wire contract:
//
//     authoring.get_drill_data(query, drill_stack, chart_type?, config?, operations?, ...)
//
// It names what it is drilling — the config the chart builder is editing, or
// the operations the query builder is — and `drill_stack` is the descriptor:
// literals and an action per level. This door answers with the sliced
// pipeline, which is why it is closed to anyone without an authoring seat.

import { call } from 'frappe-ui'
import type { ChartConfig } from '../../types/chart.types'
import type { Operation } from '../../types/query.types'
import type { DashboardFilterContext } from '../chart_read'
import type { DrillDimension, DrillLevel, DrillLevelData } from './drill_stack'

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
