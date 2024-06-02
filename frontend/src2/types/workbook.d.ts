type InsightsWorkbook = {
	name: string
	title: string
	queries: InsightsWorkbookQuery[]
	charts: InsightsWorkbookChart[]
}
type InsightsWorkbookQuery = {
	query: string
}
type InsightsWorkbookChart = {
	chart: string
}