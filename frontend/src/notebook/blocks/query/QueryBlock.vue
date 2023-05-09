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
	minimizeQuery: false,
	minimizeResult: true,
	showQueryActions: false,
	query: query,
})
provide('state', state)

state.removeQuery = () => {
	query.delete().then(() => emit('remove'))
}

const blockRef = ref(null)
// if clicked anywhere within the block, show query actions
const showQueryActions = (e) => {
	state.showQueryActions = blockRef.value?.contains(e.target)
}
onMounted(() => {
	document.addEventListener('click', showQueryActions)
})
onBeforeUnmount(() => {
	document.removeEventListener('click', showQueryActions)
})
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

	<UsePopover
		v-if="blockRef"
		:show="state.showQueryActions"
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
