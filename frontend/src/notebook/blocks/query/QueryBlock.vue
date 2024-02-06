<script setup>
import NativeQueryEditor from '@/query/NativeQueryEditor.vue'
import ResultSection from '@/query/ResultSection.vue'
import ResultFooter from '@/query/visual/ResultFooter.vue'
import useQuery from '@/query/resources/useQuery'
import useQueryStore from '@/stores/queryStore'
import { provide, reactive } from 'vue'
import QueryBlockHeader from './QueryBlockHeader.vue'

const emit = defineEmits(['setQuery', 'remove'])
const props = defineProps({ query: String })

let query = null
if (!props.query) {
	const queryDoc = await useQueryStore().create()
	emit('setQuery', queryDoc.name)
	query = useQuery(queryDoc.name)
	await query.reload()
} else {
	query = useQuery(props.query)
	await query.reload()
}
await query.convertToNative()

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
	useQueryStore()
		.delete(query.doc.name)
		.then(() => emit('remove'))
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
				class="flex min-h-[10rem] w-full flex-1 overflow-hidden border-t"
			>
				<NativeQueryEditor></NativeQueryEditor>
			</div>
		</transition>

		<div
			v-if="state.query.results?.formattedResults?.length > 1 && !state.minimizeResult"
			class="group relative flex max-h-80 flex-col overflow-hidden border-t bg-white"
		>
			<ResultSection>
				<template #footer>
					<ResultFooter></ResultFooter>
				</template>
			</ResultSection>
		</div>
	</div>
	<div v-else class="flex h-20 w-full flex-col items-center justify-center">
		<LoadingIndicator class="mb-2 w-6 text-gray-300" />
	</div>
</template>
