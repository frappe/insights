// The `insights.dashboard` island: a saved dashboard, wherever a host mounts it.

import DashboardIsland from './DashboardIsland.vue'
import { mountIsland } from './entry'

export function mount(el: HTMLElement, context: Record<string, any>) {
	return mountIsland(DashboardIsland, el, context)
}
