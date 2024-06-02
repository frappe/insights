import { InjectionKey, computed, reactive, toRefs, watch, watchEffect } from 'vue'
import { useRouter } from 'vue-router'
import { getUniqueId } from '../helpers'
import useDocumentResource from '../helpers/resource'
import { createToast } from '../helpers/toasts'
import { watchOnce } from '@vueuse/core'
import useQuery from '../query/query'
import useChart from '../charts/chart'

export default function useWorkbook(name: string) {
	const resource = getWorkbookResource(name)

	const workbook = reactive({
		...toRefs(resource),

		activeTabType: '',
		activeTabName: '',

		setActiveTab(type: string, name: string) {
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

	workbook.onBeforeSave(() => {
		return Promise.all([
			...workbook.doc.queries.map(async (row) => {
				return useQuery(row.query)
					.save()
					.then((doc) => {
						row.query = doc ? doc.name : row.query
					})
			}),
			...workbook.doc.charts.map(async (row) => {
				return useChart(row.chart)
					.save()
					.then((doc) => {
						row.chart = doc ? doc.name : row.chart
					})
			}),
		])
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
			name: '',
			title: '',
			queries: [],
			charts: [],
		},
	})
	return workbook
}
