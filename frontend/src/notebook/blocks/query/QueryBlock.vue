<script setup>
import useQueries from '@/query/useQueries'
import { provide, reactive } from 'vue'
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
	await query.reload()
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
</template>
