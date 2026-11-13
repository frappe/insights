// The `insights.chart` island: one saved chart.

import ChartIsland from './ChartIsland.vue'
import { mountIsland } from './entry'

export function mount(el: HTMLElement, context: Record<string, any>) {
	return mountIsland(ChartIsland, el, context)
}
