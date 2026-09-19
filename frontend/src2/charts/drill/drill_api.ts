// Every server call the drill makes.
//
// The whole client-side reading of the drill endpoint is one file to reconcile
// if it answers differently from what this expects. Nothing above this module
// knows an endpoint's name, its argument names, or the shape of its answer
// beyond `DrillLevelData`.
//
// There are two endpoints, one per source:
//
//     view.get_drill_data(chart, dashboard?, filters?, drill_stack)
//     authoring.get_drill_data(query, drill_stack, chart_type?, config?, operations?, ...)
//
// A reader names the saved chart and the grid it sits on, and gets rows back.
// The builder names what it is drilling — the config the chart builder is
// editing, or the operations the query builder is — and gets the sliced pipeline
// with them, which is why that endpoint is closed to anyone without an Insights
// role. `drill_stack` is the same descriptor either way: literals and an action
// per level.

import { call } from 'frappe-ui'
import type { ChartConfig } from '../../types/chart.types'
import type { Operation } from '../../types/query.types'
import type { FilterValues } from '../../types/workbook.types'
import type { DashboardFilterContext } from '../chart_view'
import type { DrillDimension, DrillLevel, DrillLevelData } from './drill_stack'

/** What a reader is drilling: the saved chart, and the grid it was clicked on. */
export type ViewDrillSubject = {
	chart: string
	dashboard?: string
	filters?: FilterValues
}

export function fetchViewDrillData(
	subject: ViewDrillSubject,
	drill_stack: DrillLevel[],
): Promise<DrillLevelData> {
	return call('insights.api.view.get_drill_data', { ...subject, drill_stack })
}

/**
 * What an authoring surface is drilling. Both forms name the source query — it
 * carries the data source and the read check — and then say what shape sits on
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
		// what the reader narrowed this one card to. A level that leaves it out
		// counts rows the card itself does not draw
		card_filters: filterContext?.cardFilters,
	})
}

export function fetchAuthoringDrillDimensions(
	subject: AuthoringDrillSubject,
): Promise<DrillDimension[]> {
	return call('insights.api.authoring.get_drill_dimensions', subject).then(
		(response) => (response as { dimensions?: DrillDimension[] })?.dimensions || [],
	)
}
