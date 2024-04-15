import useDataModel from '@/datamodel/useDataModel'
import { useStorage, watchDebounced } from '@vueuse/core'
import { InjectionKey, reactive } from 'vue'

export default function useAnalysis(name: string, modelName: string) {
	const analysis = reactive({
		name,
		modelName,
		model: useDataModel(modelName),
		title: 'Sales Analysis',
		charts: [] as AnalysisChart[],
		activeTabIdx: -1,

		addChart,
		removeChart,
		setCurrentTab,

		serialize() {
			return {
				name: analysis.name,
				title: analysis.title,
				modelName: analysis.modelName,
				charts: analysis.charts,
				activePageIdx: analysis.activeTabIdx,
			}
		},
	})

	const storedAnalysis = useStorage(`insights:analysis:${name}`, {} as AnalysisSerialized)
	if (storedAnalysis.value.name === name) {
		Object.assign(analysis, storedAnalysis.value)
	}
	watchDebounced(analysis, () => (storedAnalysis.value = analysis.serialize()), {
		deep: true,
		debounce: 1000,
	})

	function setCurrentTab(index: number) {
		analysis.activeTabIdx = index
	}

	function addChart() {
		const chartIndex = analysis.charts.length + 1
		analysis.charts.push({
			name: 'new-chart-' + chartIndex,
			title: 'Chart ' + chartIndex,
		})
		setCurrentTab(analysis.charts.length - 1)
	}

	function removeChart(index: number) {
		analysis.charts.splice(index, 1)
		if (analysis.activeTabIdx >= analysis.charts.length) {
			setCurrentTab(analysis.charts.length - 1)
		}
	}

	return analysis
}

export type Analysis = ReturnType<typeof useAnalysis>
export type AnalysisSerialized = ReturnType<Analysis['serialize']>
export const analysisKey = Symbol() as InjectionKey<Analysis>

export type AnalysisChart = {
	name: string
	title: string
}
