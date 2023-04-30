<script setup>
import useDataSources from '@/datasource/useDataSources'
import useQueries from '@/query/useQueries'
import { provide, reactive } from 'vue'
import ChartOptionsDropdown from './ChartOptionsDropdown.vue'
import QueryBlockHeader from './QueryBlockHeader.vue'
import QueryChart from './QueryChart.vue'
import QueryEditorNative from './QueryEditorNative.vue'
import QueryResult from './QueryResult.vue'
import ResultChartSwitcher from './ResultChartSwitcher.vue'
import useQuery from './useQuery'

const emit = defineEmits(['setQuery', 'remove'])
const props = defineProps({ query: String })
let queryName = props.query
if (!queryName) {
	const sources = await useDataSources()
	await sources.reload()
	const source = sources.list[0]
	queryName = await useQueries().create(source.name)
	emit('setQuery', queryName)
}
const query = useQuery(queryName)
provide('query', query)
const state = reactive({
	dataSource: '',
	resultOrChart: 'Result',
	minimizeQuery: false,
	showQueryActions: false,
	query: query,
})
provide('state', state)

state.removeQuery = () => {
	query.delete().then(() => emit('remove'))
}
</script>

<template>
	<div class="relative my-6 overflow-hidden rounded border bg-white">
		<QueryBlockHeader />
		<transition name="fade" mode="out-in">
			<div
				v-show="state.query.doc.name && !state.minimizeQuery"
				class="mb-2 w-full flex-1 overflow-hidden"
				@mouseover="state.showQueryActions = true"
				@mouseleave="state.showQueryActions = false"
			>
				<QueryEditorNative />
			</div>
		</transition>

		<div
			v-if="state.query.doc?.results?.length > 1"
			class="relative flex h-[20rem] max-h-80 flex-col overflow-hidden border-t bg-white"
		>
			<QueryResult v-if="state.resultOrChart == 'Result'" />
			<QueryChart v-if="state.resultOrChart == 'Visualize'" />

			<div class="absolute right-1.5 top-1.5 flex items-center space-x-2">
				<ChartOptionsDropdown />
				<ResultChartSwitcher />
			</div>
		</div>
	</div>
</template>
