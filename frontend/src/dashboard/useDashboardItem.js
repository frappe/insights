import { computed, reactive, defineAsyncComponent, markRaw } from 'vue'
import { useChart } from '@/utils/charts'
import { getFormattedResult } from '@/utils/query/results'

export default function useDashboardItem(dashboard, item) {
	if (item.item_type == 'Chart') {
		const chartDataRequest = dashboard.fetchChartData(item.chart)
		const queryColumnsRequest = dashboard.fetchQueryColumns(item.query)
		const formattedResult = computed(() =>
			getFormattedResult(chartDataRequest.data, queryColumnsRequest.data)
		)
		const chart = useChart({ chartID: item.chart, data: formattedResult })
		chart.loading = computed(() => chartDataRequest.loading || queryColumnsRequest.loading)
		return chart
	}

	if (item.item_type == 'Filter') {
		const component = markRaw(defineAsyncComponent(() => import('./DashboardFilter.vue')))
		const componentProps = computed(() => ({ item }))

		return reactive({
			component,
			componentProps,
		})
	}

	if (item.item_type == 'Text') {
		const component = markRaw(defineAsyncComponent(() => import('./DashboardText.vue')))
		const componentProps = computed(() => ({ item }))

		return reactive({
			component,
			componentProps,
		})
	}
}
