<script setup lang="ts">
import { provide } from 'vue'
import QueryBuilderEmptyState from './QueryBuilderEmptyState.vue'
import QueryBuilderSidebar from './QueryBuilderSidebar.vue'
import QueryBuilderTable from './QueryBuilderTable.vue'
import QueryBuilderToolbar from './QueryBuilderToolbar.vue'
import useQuery, { Query } from './useQuery'

type QueryBuilderProps = { queryName: string } | { query: Query }
const props = defineProps<QueryBuilderProps>()
const query = 'query' in props ? props.query : useQuery(props.queryName)
provide('query', query)
</script>

<template>
	<QueryBuilderEmptyState v-if="!query.dataSource" />
	<div v-show="query.dataSource" class="relative flex h-full w-full divide-x overflow-hidden">
		<div class="relative flex w-[16rem] flex-shrink-0 flex-col overflow-y-auto bg-white">
			<QueryBuilderSidebar></QueryBuilderSidebar>
		</div>
		<div class="flex h-full w-full flex-col overflow-hidden pt-0 pr-0">
			<QueryBuilderToolbar></QueryBuilderToolbar>
			<QueryBuilderTable></QueryBuilderTable>
		</div>
	</div>
</template>
