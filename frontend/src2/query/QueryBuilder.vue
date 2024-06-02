<script setup lang="ts">
import { inject, provide } from 'vue'
import QueryBuilderSourceSelector from './components/QueryBuilderSourceSelector.vue'
import QueryBuilderTable from './components/QueryBuilderTable.vue'
import QueryBuilderToolbar from './components/QueryBuilderToolbar.vue'
import QueryOperations from './components/QueryOperations.vue'
import useQuery from './query'

const props = defineProps<{ queryId: string }>()
const query = useQuery(props.queryId)
provide('query', query)
</script>

<template>
	<QueryBuilderSourceSelector v-if="!query.doc.operations.length" />
	<div v-else class="relative flex h-full w-full divide-x overflow-hidden bg-white">
		<div class="flex h-full w-full flex-col overflow-hidden pt-0 pr-0">
			<QueryBuilderToolbar></QueryBuilderToolbar>
			<QueryBuilderTable></QueryBuilderTable>
		</div>
	</div>
	<div
		class="relative flex h-full w-[17rem] flex-shrink-0 flex-col overflow-y-auto border-l bg-white"
	>
		<QueryOperations />
	</div>
</template>
