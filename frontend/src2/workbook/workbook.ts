import { watchOnce } from '@vueuse/core'
import { InjectionKey, reactive, toRefs, watchEffect } from 'vue'
import { useRouter } from 'vue-router'
import useChart from '../charts/chart'
import { getUniqueId } from '../helpers'
import useDocumentResource from '../helpers/resource'
import { createToast } from '../helpers/toasts'
import useQuery from '../query/query'

export default function useWorkbook(name: string) {
	const resource = getWorkbookResource(name)

	type ActiveTabType = 'query' | 'chart' | 'dashboard' | ''
	const workbook = reactive({
		...toRefs(resource),

		activeTabType: '' as ActiveTabType,
		activeTabIdx: 0,

		setActiveTab(type: ActiveTabType, idx: number) {
			workbook.activeTabType = type
			workbook.activeTabIdx = idx
		},
		isActiveTab(queryOrChartName: string) {
			return (
				(workbook.activeTabType === 'query' &&
					workbook.doc.queries[workbook.activeTabIdx].query === queryOrChartName) ||
				(workbook.activeTabType === 'chart' &&
					workbook.doc.charts[workbook.activeTabIdx].chart === queryOrChartName) ||
				(workbook.activeTabType === 'dashboard' &&
					workbook.doc.dashboards[workbook.activeTabIdx].name === queryOrChartName)
			)
		},

		addQuery() {
			const queryName = 'new-query-' + getUniqueId()
			workbook.doc.queries.push({ query: queryName })
			workbook.setActiveTab('query', workbook.doc.queries.length - 1)
		},

		removeQuery(queryName: string) {
			const row = workbook.doc.queries.find((row) => row.query === queryName)
			if (row) {
				workbook.doc.queries.splice(workbook.doc.queries.indexOf(row), 1)
				if (workbook.isActiveTab(queryName)) {
					workbook.setActiveTab('', 0)
				}
			}
		},

		addChart() {
			const name = 'new-chart-' + getUniqueId()
			workbook.doc.charts.push({ chart: name })
			workbook.setActiveTab('chart', workbook.doc.charts.length - 1)
		},

		removeChart(chartName: string) {
			const row = workbook.doc.charts.find((row) => row.chart === chartName)
			if (row) {
				workbook.doc.charts.splice(workbook.doc.charts.indexOf(row), 1)
				if (workbook.isActiveTab(chartName)) {
					workbook.setActiveTab('', 0)
				}
			}
		},

		addDashboard() {
			const name = 'new-dashboard-' + getUniqueId()
			const idx = workbook.doc.dashboards.length
			const title = `Dashboard ${idx + 1}`
			workbook.doc.dashboards.push({ name, title })
			workbook.setActiveTab('dashboard', idx)
		},

		removeDashboard(dashboardName: string) {
			const idx = workbook.doc.dashboards.findIndex((row) => row.name === dashboardName)
			if (idx === -1) return
			workbook.doc.dashboards.splice(idx, 1)
			if (workbook.isActiveTab(dashboardName)) {
				workbook.setActiveTab('', 0)
			}
		},
	})

	const router = useRouter()
	workbook.onAfterInsert(() => {
		router.replace(`/workbook/${workbook.doc.name}`)
	})
	watchEffect(() => {
		if (workbook.saving) {
			createToast({
				title: 'Saving...',
				variant: 'info',
			})
			watchOnce(
				() => workbook.saving,
				() => {
					createToast({
						title: 'Saved',
						variant: 'success',
					})
				}
			)
		}
	})

	workbook.onBeforeSave(async () => {
		const queryPromises = workbook.doc.queries.map(async (row) => {
			const query = await useQuery(row.query).save()
			row.query = query.name
		})
		const chartPromises = workbook.doc.charts.map(async (row) => {
			const chart = await useChart(row.chart).save()
			row.chart = chart.name
		})
		await Promise.all(queryPromises)
		await Promise.all(chartPromises)

		workbook.doc.dashboards.forEach(
			(row) => (row.name = row.name.startsWith('new-dashboard-') ? '' : row.name)
		)
	})

	// set first tab as active
	watchOnce(
		() => workbook.doc.queries,
		() => {
			if (workbook.doc.queries.length) {
				workbook.setActiveTab('query', 0)
			}
		}
	)

	return workbook
}

export type Workbook = ReturnType<typeof useWorkbook>
export const workbookKey = Symbol() as InjectionKey<Workbook>

function getWorkbookResource(name: string) {
	const doctype = 'Insights Workbook'
	const workbook = useDocumentResource<InsightsWorkbook>(doctype, name, {
		initialDoc: {
			doctype,
			name: '',
			title: '',
			queries: [],
			charts: [],
			dashboards: [],
		},
	})
	return workbook
}
