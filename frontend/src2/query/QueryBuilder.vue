<script setup lang="ts">
import { provide } from 'vue'
import { WorkbookQuery } from '../types/workbook.types'
import QueryBuilderSourceSelector from './components/QueryBuilderSourceSelector.vue'
import QueryBuilderTable from './components/QueryBuilderTable.vue'
import QueryBuilderToolbar from './components/QueryBuilderToolbar.vue'
import QueryInfo from './components/QueryInfo.vue'
import QueryOperations from './components/QueryOperations.vue'
import useQuery from './query'

const props = defineProps<{ query: WorkbookQuery }>()
const query = useQuery(props.query)
provide('query', query)
</script>

<template>
	<div class="flex flex-1 overflow-hidden">
		<QueryBuilderSourceSelector v-if="!query.doc.operations.length" />
		<div v-else class="relative flex h-full w-full flex-col gap-4 overflow-hidden border-l p-4">
			<QueryBuilderToolbar></QueryBuilderToolbar>
			<div class="flex flex-1 overflow-hidden rounded shadow">
				<QueryBuilderTable></QueryBuilderTable>
			</div>
		</div>
		<div
			class="relative flex h-full w-[17rem] flex-shrink-0 flex-col gap-1 divide-y overflow-y-auto bg-white shadow-sm"
		>
			<QueryInfo />
			<QueryOperations />
		</div>
	</div>
</template>
