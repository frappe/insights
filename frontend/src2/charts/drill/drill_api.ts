// The one door the drill goes through.
//
// Every server call the drill makes is here, so the whole client-side reading of
// `insights.api.viewer.get_drill_data` is one file to reconcile if the endpoint
// answers differently from what this expects. Nothing above this module knows
// the endpoint's name, its argument names, or the shape of its answer beyond
// `DrillLevelData`.
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

import { call } from 'frappe-ui'
import type { ViewerFilters } from '../../dashboard/viewer'
import type { DrillLevel, DrillLevelData } from './drill_stack'

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
