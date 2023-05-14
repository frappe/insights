<script setup>
import useDataSources from '@/datasource/useDataSources'
import InputWithPopover from '@/notebook/blocks/query/builder/InputWithPopover.vue'
import useQueries from '@/query/useQueries'
import { computed, provide, reactive, ref } from 'vue'
import BlockAction from '../BlockAction.vue'
import BlockActions from '../BlockActions.vue'
import QueryBlockHeader from './QueryBlockHeader.vue'
import QueryEditor from './QueryEditor.vue'
import QueryResult from './QueryResult.vue'
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
	minimizeResult: true,
	minimizeQuery: false,
	showQueryActions: false,
	query: query,
})
provide('state', state)

state.removeQuery = () => {
	query.delete().then(() => emit('remove'))
}

const blockRef = ref(null)
const sources = useDataSources()
sources.reload()
const sourceOptions = computed(() =>
	sources.list.map((source) => ({
		label: source.title,
		value: source.name,
		description: source.name,
	}))
)
const selectedSource = computed(() => {
	return sourceOptions.value.find((op) => op.value === query.doc.data_source)
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
				<QueryBuilder v-else :name="state.query.doc.name" />
			</div>
		</transition>

		<div
			v-if="state.query.doc?.results?.length > 1 && !state.minimizeResult"
			class="group relative flex h-[20rem] max-h-80 flex-col overflow-hidden border-t bg-white"
		>
			<QueryResult />
		</div>
	</div>
	<div v-else class="flex h-20 w-full flex-col items-center justify-center">
		<LoadingIndicator class="mb-2 w-6 text-gray-300" />
	</div>

	<BlockActions :blockRef="blockRef">
		<BlockAction class="!px-0">
			<div class="relative flex w-full items-center text-gray-800 [&>div]:w-full">
				<InputWithPopover
					placeholder="Data Source"
					:items="sourceOptions"
					:value="selectedSource"
					placement="bottom-end"
					:disableFilter="true"
					@update:modelValue="state.query.doc.data_source = $event.value"
				></InputWithPopover>
				<p class="pointer-events-none absolute right-0 top-0 flex h-full items-center px-2">
					<FeatherIcon name="chevron-down" class="h-4 w-4 text-gray-400" />
				</p>
			</div>
		</BlockAction>

		<BlockAction icon="play" label="Execute" :action="state.query.execute"> </BlockAction>
		<BlockAction
			:icon="state.minimizeResult ? 'maximize-2' : 'minimize-2'"
			:label="state.minimizeResult ? 'Show Results' : 'Hide Results'"
			:action="() => (state.minimizeResult = !state.minimizeResult)"
		>
		</BlockAction>
		<BlockAction
			:icon="state.minimizeQuery ? 'maximize-2' : 'minimize-2'"
			:label="state.minimizeQuery ? 'Show Query' : 'Hide Query'"
			:action="() => (state.minimizeQuery = !state.minimizeQuery)"
		>
		</BlockAction>
		<BlockAction icon="trash" label="Delete" :action="state.removeQuery"> </BlockAction>
	</BlockActions>
</template>