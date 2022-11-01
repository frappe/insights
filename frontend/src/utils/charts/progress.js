import { reactive, defineAsyncComponent } from 'vue'
import { isEmptyObj } from '@/utils'

export default function useProgressChart() {
	const chart = reactive({
		type: 'Progress',
		icon: 'hash',
		getComponent,
		buildComponentProps,
	})

	function getComponent() {
		return defineAsyncComponent(() => import('@/components/Query/Visualize/ProgressChart.vue'))
	}

	function buildComponentProps(queryChart) {
		if (queryChart.data.length == 0) return
		if (isEmptyObj(queryChart.config.progressColumn, queryChart.config.targetColumn)) return

		const progressColIndex = queryChart.data[0].findIndex((col) =>
			col.includes(queryChart.config.progressColumn.label)
		)
		const targetColIndex = queryChart.data[0].findIndex((col) =>
			col.includes(queryChart.config.targetColumn.label)
		)

		return {
			title: queryChart.title,
			progress: queryChart.data[1][progressColIndex],
			target: queryChart.data[1][targetColIndex],
			options: queryChart.options,
		}
	}

	return chart
}
