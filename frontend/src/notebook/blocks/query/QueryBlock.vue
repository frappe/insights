<script setup>
import useDataSourceStore from '@/stores/dataSourceStore'
import InputWithPopover from '@/notebook/blocks/query/builder/InputWithPopover.vue'
import useQueries from '@/query/useQueries'
import { copyToClipboard } from '@/utils'
import { computed, inject, provide, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
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
	const queryDoc = await useQueries().create()
	emit('setQuery', queryDoc.name)
	query = useQuery(queryDoc.name)
	props.is_native ? await query.convertToNative() : await query.convertToAssisted()
} else {
	query = useQuery(props.query)
}

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
const page = inject('page')
const router = useRouter()
function duplicateQuery() {
	query.duplicate().then((name) => {
		if (page?.addQuery) {
			page.addQuery(props.is_native ? 'query-editor' : 'query-builder', name)
		} else {
			router.push(`/query/build/${name}`)
		}
	})
}

const show_sql_dialog = ref(false)
const formattedSQL = computed(() => {
	return query.doc.sql.replaceAll('\n', '<br>').replaceAll('      ', '&ensp;&ensp;&ensp;&ensp;')
})

const sources = useDataSourceStore()

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
			class="group relative flex max-h-80 flex-col overflow-hidden border-t bg-white"
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

		<BlockAction
			label="Save"
			icon="save"
			:action="state.query.save"
			:loading="state.query.loading"
		/>
		<BlockAction
			icon="play"
			label="Execute"
			:action="() => state.query.execute() || (state.minimizeResult = false)"
			:loading="state.query.executing"
		/>
		<BlockAction
			:icon="state.minimizeResult ? 'maximize-2' : 'minimize-2'"
			:label="state.minimizeResult ? 'Show Results' : 'Hide Results'"
			:action="() => (state.minimizeResult = !state.minimizeResult)"
		/>
		<BlockAction
			:icon="state.minimizeQuery ? 'maximize-2' : 'minimize-2'"
			:label="state.minimizeQuery ? 'Show Query' : 'Hide Query'"
			:action="() => (state.minimizeQuery = !state.minimizeQuery)"
		/>
		<BlockAction
			label="Duplicate"
			icon="copy"
			:action="duplicateQuery"
			:loading="state.query.duplicating"
		/>
		<BlockAction
			v-if="!props.is_native && query.doc.sql"
			label="View SQL"
			icon="code"
			:action="() => (show_sql_dialog = true)"
		/>
		<BlockAction
			icon="trash"
			label="Delete"
			:action="state.removeQuery"
			:loading="state.query.deleting"
		/>
	</BlockActions>

	<Dialog
		:options="{ title: 'Generated SQL', size: '3xl' }"
		v-model="show_sql_dialog"
		:dismissable="true"
	>
		<template #body-content>
			<div class="relative">
				<p
					class="rounded border bg-gray-100 p-2 text-base text-gray-600"
					style="font-family: 'Fira Code'"
					v-html="formattedSQL"
				></p>
				<Button
					icon="copy"
					variant="outline"
					class="absolute bottom-2 right-2"
					@click="copyToClipboard(query.doc.sql)"
				></Button>
			</div>
		</template>
	</Dialog>
</template>
