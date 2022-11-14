import { computed, reactive, defineAsyncComponent, markRaw } from 'vue'
import { useChart } from '@/utils/charts'
import { getFormattedResult } from '@/utils/query/results'

export default function useDashboardItem(dashboard, item) {
	if (item.item_type == 'Chart') {
		const data = dashboard.getChartData(item.chart)
		const columns = dashboard.getColumns(item.query)
		const formattedResult = getFormattedResult(data, columns)
		return useChart({ chartID: item.chart, data: formattedResult })
	}

	if (item.item_type == 'Filter') {
		const component = markRaw(defineAsyncComponent(() => import('./DashboardFilter.vue')))
		const componentProps = computed(() => ({ item }))

		return reactive({
			component,
			componentProps,
		})
	}
}
