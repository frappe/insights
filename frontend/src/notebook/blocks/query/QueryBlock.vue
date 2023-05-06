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
const props = defineProps({ query: String, is_native: Boolean })

let query = null
if (!props.query) {
	const sources = await useDataSources()
	await sources.reload()
	const source = sources.list[0]
	const query_name = await useQueries().create(source.name)
	emit('setQuery', query_name)
	query = useQuery(query_name)
	if (props.is_native) query.convertToNative()
} else {
	query = useQuery(props.query)
}

query.autosave = true
provide('query', query)

const state = reactive({
	dataSource: '',
	resultOrChart: 'Result',
	minimizeQuery: false,
	minimizeResult: false,
	showQueryActions: false,
	query: query,
})
provide('state', state)

state.removeQuery = () => {
	query.delete().then(() => emit('remove'))
}
</script>

<template>
	<div v-if="query.doc.name" class="relative my-6 overflow-hidden rounded border bg-white">
		<QueryBlockHeader />
		<transition name="fade" mode="out-in">
			<div
				v-show="state.query.doc.name && !state.minimizeQuery"
				class="mb-2 w-full flex-1 overflow-hidden"
				@mouseover="state.showQueryActions = true"
				@mouseleave="state.showQueryActions = false"
			>
				<QueryEditorNative v-if="props.is_native" />
				<div v-else></div>
			</div>
		</transition>

		<div
			v-if="state.query.doc?.results?.length > 1 && !state.minimizeResult"
			class="group relative flex h-[20rem] max-h-80 flex-col overflow-hidden border-t bg-white"
		>
			<QueryResult v-if="state.resultOrChart == 'Result'" />
			<QueryChart v-if="state.resultOrChart == 'Visualize'" />

			<div class="absolute right-1.5 top-1.5 flex items-center space-x-2">
				<Button
					class="flex h-7 cursor-pointer items-center rounded-md !border !border-gray-200 bg-white !px-2 !text-sm !text-gray-600 opacity-0 transition-opacity hover:bg-gray-50 hover:text-gray-800 group-hover:opacity-100"
					@click="state.minimizeResult = !state.minimizeResult"
				>
					<FeatherIcon
						:name="state.minimizeResult ? 'maximize-2' : 'minimize-2'"
						class="h-3.5 w-3.5"
					></FeatherIcon>
				</Button>
				<ChartOptionsDropdown />
				<ResultChartSwitcher />
			</div>
		</div>
	</div>
	<div v-else class="flex h-20 w-full flex-col items-center justify-center">
		<LoadingIndicator class="mb-2 w-6 text-gray-300" />
	</div>
</template>
