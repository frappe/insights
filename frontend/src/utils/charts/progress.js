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
		if (isEmptyObj(queryChart.config.progressColumn) || !queryChart.config.target) return

		const progressColIndex = queryChart.data[0].findIndex((col) =>
			col.includes(queryChart.config.progressColumn.label)
		)

		return {
			title: queryChart.title,
			options: queryChart.options,
			progress: queryChart.data[1][progressColIndex],
			target: getTarget(queryChart),
		}
	}

	function getTarget(queryChart) {
		if (typeof queryChart.config.target === 'object') {
			const targetColIndex = queryChart.data[0].findIndex((col) =>
				col.includes(queryChart.config.target.label)
			)
			return queryChart.data[1][targetColIndex]
		} else {
			return parseInt(queryChart.config.target)
		}
	}

	return chart
}
