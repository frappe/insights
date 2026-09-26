// The `insights.dashboard` island: one saved dashboard.

import DashboardIsland from './DashboardIsland.vue'
import { mountIsland } from './entry'

export function mount(el: HTMLElement, context: Record<string, any>) {
	return mountIsland(DashboardIsland, el, context)
}
