import { computed, reactive, defineAsyncComponent, markRaw } from 'vue'
import { useChart } from '@/utils/charts'

export default function useDashboardItem(dashboard, item) {
	if (item.item_type == 'Chart') {
		const data = dashboard.getChartData(item.chart)
		return useChart({ chartID: item.chart, data })
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
