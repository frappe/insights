type InsightsWorkbook = {
	doctype: 'Insights Workbook'
	name: string
	title: string
	queries: InsightsWorkbookQuery[]
	charts: InsightsWorkbookChart[]
	dashboards: WorkbookDashboard[]
}
type InsightsWorkbookQuery = {
	query: string
}
type InsightsWorkbookChart = {
	chart: string
}
type WorkbookDashboard = {
	name: string
	title?: string
	items?: WorkbookDashboardItem[]
}
type WorkbookDashboardItem = {
	layout: {
		x: number
		y: number
		w: number
		h: number
	}
} & (
	| {
			type: 'chart'
			chart: string
	  }
	| {
			type: 'filter'
			filter: object
	  }
	| {
			type: 'text'
			text: string
	  }
)
