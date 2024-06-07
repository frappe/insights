import { reactive } from 'vue'
import { getUniqueId } from '../helpers'
import { WorkbookDashboard } from '../workbook/workbook'

const dashboards = new Map<string, Dashboard>()

export default function useDashboard(workbookDashboard: WorkbookDashboard) {
	const existingDashboard = dashboards.get(workbookDashboard.name)
	if (existingDashboard) return existingDashboard

	const dashboard = makeDashboard(workbookDashboard)
	dashboards.set(workbookDashboard.name, dashboard)
	return dashboard
}

function makeDashboard(workbookDashboard: WorkbookDashboard) {
	const dashboard = reactive({
		doc: workbookDashboard,

		editing: true,
		filters: [] as FilterArgs[],

		activeItemIdx: null as number | null,
		setActiveItem(index: number) {
			dashboard.activeItemIdx = index
		},

		addChart(chart: string[] | string) {
			const _chart = Array.isArray(chart) ? chart : [chart]
			_chart.forEach((chart) => {
				dashboard.doc.items.push({
					type: 'chart',
					chart,
					layout: {
						i: getUniqueId(),
						x: 0,
						y: 0,
						w: 10,
						h: 12,
					},
				})
			})
		},

		removeItem(index: number) {
			dashboard.doc.items.splice(index, 1)
		},

		setFilters(filters: FilterArgs[]) {
			dashboard.filters = filters
			dashboard.refresh()
		},

		refresh() {},
	})

	return dashboard
}

export type Dashboard = ReturnType<typeof makeDashboard>
