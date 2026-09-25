// Every server call the drill makes.
//
// The whole client-side reading of the drill endpoint is one file to reconcile
// if it answers differently from what this expects. Nothing above this module
// knows an endpoint's name, its argument names, or the shape of its answer
// beyond `DrillLevelData`.
//
// Two sources: `insights.api.view` and `insights.api.authoring`. A reader sends
// the saved chart and its dashboard, and gets rows back. The server sorts,
// searches and pages them, because the pipeline that would let the client do it
// never leaves the server.
// The builder sends what it is drilling: the config the chart builder is
// editing, or the operations the query builder is editing. Its rows are read
// the same way, plus the cut pipeline for "open as query". That is why the
// authoring endpoint needs an Insights role. `drill_stack` is the same
// descriptor for both: literals and an action per level.

import { call } from 'frappe-ui'
import type { ChartConfig } from '../../types/chart.types'
import type { Operation } from '../../types/query.types'
import type { FilterValues } from '../../types/workbook.types'
import type { DashboardFilterContext } from '../chart_view'
import type {
	DrillDimension,
	DrillLevel,
	DrillLevelData,
	DrillRowFilter,
	DrillRowsReading,
	DrillRowsSource,
} from './drill_stack'

export type ViewDrillSubject = {
	chart: string
	dashboard?: string
	filters?: FilterValues
}

export function fetchViewDrillData(
	subject: ViewDrillSubject,
	drill_stack: DrillLevel[],
	// Left out for a level nobody has changed yet, and for a breakdown, which
	// uses none of it
	reading?: DrillRowsReading,
): Promise<DrillLevelData> {
	return call('insights.api.view.get_drill_data', { ...subject, drill_stack, ...reading })
}

/** A file needs no page, so the reading is sent without it. */
export function downloadViewDrillRows(
	subject: ViewDrillSubject,
	drill_stack: DrillLevel[],
	reading: DrillRowsReading,
	format: string,
): Promise<string> {
	return call('insights.api.view.download_drill_rows', {
		...subject,
		drill_stack,
		row_filters: reading.row_filters,
		sort: reading.sort,
		find: reading.find,
		format,
	})
}

export function fetchViewDrillRowsValues(
	subject: ViewDrillSubject,
	drill_stack: DrillLevel[],
	column: string,
	search_term: string,
	row_filters: DrillRowFilter[],
): Promise<string[]> {
	return call('insights.api.view.get_drill_rows_values', {
		...subject,
		drill_stack,
		column,
		search_term,
		row_filters,
	})
}

export function fetchViewDrillRowsRange(
	subject: ViewDrillSubject,
	drill_stack: DrillLevel[],
	column: string,
	row_filters: DrillRowFilter[],
): Promise<[number, number] | undefined> {
	return call('insights.api.view.get_drill_rows_range', {
		...subject,
		drill_stack,
		column,
		row_filters,
	})
}

/**
 * What the builder is drilling. Both forms name the source query — it
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
	// the saved chart this level belongs to, when the caller is not a dashboard.
	// The chart decides whose permissions filter the rows, so a level that leaves
	// it out can read different rows from the card it was opened from
	declaringChart?: string,
	reading?: DrillRowsReading,
): Promise<DrillLevelData> {
	return call('insights.api.authoring.get_drill_data', {
		...authoringArgs(subject, filterContext, declaringChart),
		drill_stack,
		...reading,
	})
}

export function authoringDrillRows(
	subject: AuthoringDrillSubject,
	drill_stack: DrillLevel[],
	filterContext?: DashboardFilterContext,
	declaringChart?: string,
): DrillRowsSource {
	const args = () => ({ ...authoringArgs(subject, filterContext, declaringChart), drill_stack })
	return {
		read: (reading) =>
			fetchAuthoringDrillData(subject, drill_stack, filterContext, declaringChart, reading),
		download: (reading, format) =>
			call('insights.api.authoring.download_drill_rows', {
				...args(),
				row_filters: reading.row_filters,
				sort: reading.sort,
				find: reading.find,
				format,
			}),
		values: (column, search_term, row_filters) =>
			call('insights.api.authoring.get_drill_rows_values', {
				...args(),
				column,
				search_term,
				row_filters,
			}),
		range: (column, row_filters) =>
			call('insights.api.authoring.get_drill_rows_range', { ...args(), column, row_filters }),
	}
}

function authoringArgs(
	subject: AuthoringDrillSubject,
	filterContext?: DashboardFilterContext,
	declaringChart?: string,
) {
	return {
		...subject,
		chart_name: filterContext?.chart ?? declaringChart,
		// the saved dashboard: a user who cannot write the chart gets filters
		// routed by it
		dashboard: filterContext?.dashboard,
		dashboard_items: filterContext?.items,
		filters: filterContext?.filters,
		// what the reader narrowed this one card to. A level that leaves it out
		// counts rows the card itself does not draw
		card_filters: filterContext?.cardFilters,
	}
}

export function fetchAuthoringDrillDimensions(
	subject: AuthoringDrillSubject,
): Promise<DrillDimension[]> {
	return call('insights.api.authoring.get_drill_dimensions', subject).then(
		(response) => (response as { dimensions?: DrillDimension[] })?.dimensions || [],
	)
}
