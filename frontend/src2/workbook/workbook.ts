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
		activeTabName: '',
		activeTabIdx: 0,

		setActiveTab(type: ActiveTabType, name: string) {
			workbook.activeTabType = type
			workbook.activeTabName = name
		},
		isActiveTab(queryOrChartName: string) {
			return workbook.activeTabName === queryOrChartName
		},

		addQuery() {
			const queryName = 'new-query-' + getUniqueId()
			workbook.doc.queries.push({ query: queryName })
			workbook.setActiveTab('query', queryName)
		},

		removeQuery(queryName: string) {
			const row = workbook.doc.queries.find((row) => row.query === queryName)
			if (row) {
				workbook.doc.queries.splice(workbook.doc.queries.indexOf(row), 1)
				if (workbook.isActiveTab(queryName)) {
					workbook.setActiveTab('', '')
				}
			}
		},

		addChart() {
			const name = 'new-chart-' + getUniqueId()
			workbook.doc.charts.push({ chart: name })
			workbook.setActiveTab('chart', name)
		},

		removeChart(chartName: string) {
			const row = workbook.doc.charts.find((row) => row.chart === chartName)
			if (row) {
				workbook.doc.charts.splice(workbook.doc.charts.indexOf(row), 1)
				if (workbook.isActiveTab(chartName)) {
					workbook.setActiveTab('', '')
				}
			}
		},

		addDashboard() {
			const name = 'new-dashboard-' + getUniqueId()
			const idx = workbook.doc.dashboards.length
			const title = `Dashboard ${idx + 1}`
			workbook.doc.dashboards.push({ name, title })
			workbook.activeTabType = 'dashboard'
			workbook.activeTabIdx = idx
		},

		removeDashboard(dashboardName: string) {
			const idx = workbook.doc.dashboards.findIndex((row) => row.name === dashboardName)
			if (idx === -1) return
			workbook.doc.dashboards.splice(idx, 1)
			if (workbook.activeTabIdx === idx) {
				workbook.activeTabType = ''
				workbook.activeTabIdx = 0
			}
		},

		getDashboard(dashboardName: string) {
			const row = workbook.doc.dashboards.find((row) => row.name === dashboardName)
			if (!row) return
			return row
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
				workbook.setActiveTab('query', workbook.doc.queries[0].query)
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
