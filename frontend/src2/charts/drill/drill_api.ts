// Every server call the drill makes.
//
// The whole client-side reading of the drill endpoint is one file to reconcile
// if it answers differently from what this expects. Nothing above this module
// knows an endpoint's name, its argument names, or the shape of its answer
// beyond `DrillLevelData`.
//
// Two sources, `insights.api.view` and `insights.api.authoring`. A reader names the saved chart and the grid it sits on, and gets rows back —
// sorted, found and paged as they asked, because the pipeline that would let
// them do it themselves is exactly what never crosses.
// The builder names what it is drilling — the config the chart builder is
// editing, or the operations the query builder is — and gets its rows read the
// same way, with the sliced pipeline beside them for "open as query", which is
// why that endpoint is closed to anyone without an Insights role. `drill_stack`
// is the same descriptor either way: literals and an action per level.

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

/** What a reader is drilling: the saved chart, and the grid it was clicked on. */
export type ViewDrillSubject = {
	chart: string
	dashboard?: string
	filters?: FilterValues
}

export function fetchViewDrillData(
	subject: ViewDrillSubject,
	drill_stack: DrillLevel[],
	// how the reader is reading a rows level. Left out for a level nobody has
	// touched yet, and for a breakdown, which takes none of it
	reading?: DrillRowsReading,
): Promise<DrillLevelData> {
	return call('insights.api.view.get_drill_data', { ...subject, drill_stack, ...reading })
}

/**
 * The same cut as a file rather than as a page. A file has no use for the page,
 * so the reading crosses without it.
 */
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

/** What a filter on one column of the cut offers to pick from. */
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
	// the saved chart this level is of, for a surface that is not a grid. It
	// declares whose permissions the rows are filtered by, so a level that
	// leaves it out reads as somebody else than the card it was opened from
	declaringChart?: string,
	// how the reader is reading a rows level, as a View's reader does
	reading?: DrillRowsReading,
): Promise<DrillLevelData> {
	return call('insights.api.authoring.get_drill_data', {
		...authoringArgs(subject, filterContext, declaringChart),
		drill_stack,
		...reading,
	})
}

/**
 * The rows level of the builder's drill, read the way a View reads one: every
 * reading is the server's, run as the chart and on the day its card was read.
 */
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
		// the saved grid, which routes a caller who may not write the chart
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
