<script setup>
import useDataSources from '@/datasource/useDataSources'
import useQueries from '@/query/useQueries'
import { slideRightTransition } from '@/utils/transitions'
import { onBeforeUnmount, onMounted, provide, reactive, ref } from 'vue'
import ChartOptionsDropdown from './ChartOptionsDropdown.vue'
import QueryBlockActions from './QueryBlockActions.vue'
import QueryBlockHeader from './QueryBlockHeader.vue'
import QueryChart from './QueryChart.vue'
import QueryEditor from './QueryEditor.vue'
import QueryResult from './QueryResult.vue'
import ResultChartSwitcher from './ResultChartSwitcher.vue'
import UsePopover from './UsePopover.vue'
import QueryBuilder from './builder/QueryBuilder.vue'
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
	props.is_native ? await query.convertToNative() : await query.convertToAssisted()
} else {
	query = useQuery(props.query)
}

query.autosave = true
provide('query', query)

const state = reactive({
	dataSource: '',
	resultOrChart: 'Result',
	minimizeResult: true,
	showQueryActions: false,
	query: query,
})
provide('state', state)

state.removeQuery = () => {
	query.delete().then(() => emit('remove'))
}

const blockRef = ref(null)
</script>

<template>
	<div
		ref="blockRef"
		v-if="query.doc.name"
		class="relative my-6 overflow-hidden rounded border bg-white"
	>
		<QueryBlockHeader />
		<transition name="fade" mode="out-in">
			<div
				v-show="state.query.doc.name && !state.minimizeQuery"
				class="mb-2 w-full flex-1 overflow-hidden"
			>
				<QueryEditor v-if="props.is_native" />
				<QueryBuilder v-else />
			</div>
		</transition>

		<div
			v-if="state.query.doc?.results?.length > 1 && !state.minimizeResult"
			class="group relative flex h-[20rem] max-h-80 flex-col overflow-hidden border-t bg-white"
		>
			<QueryResult v-if="state.resultOrChart == 'Result'" />
			<QueryChart v-if="state.resultOrChart == 'Visualize'" />

			<div class="absolute right-1.5 top-1.5 flex items-center space-x-2">
				<ChartOptionsDropdown />
				<ResultChartSwitcher />
			</div>
		</div>
	</div>

	<UsePopover
		v-if="blockRef"
		:targetElement="blockRef"
		placement="right-start"
		:transition="slideRightTransition"
	>
		<QueryBlockActions />
	</UsePopover>
	<div v-else class="flex h-20 w-full flex-col items-center justify-center">
		<LoadingIndicator class="mb-2 w-6 text-gray-300" />
	</div>
</template>
