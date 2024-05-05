<script setup lang="ts">
import { provide } from 'vue'
import QueryBuilderEmptyState from './QueryBuilderEmptyState.vue'
import QueryBuilderTable from './QueryBuilderTable.vue'
import QueryBuilderToolbar from './QueryBuilderToolbar.vue'
import QueryOperations from './QueryOperations.vue'
import { Query } from './useQuery'

type QueryBuilderProps = { query: Query }
const props = defineProps<QueryBuilderProps>()
provide('query', props.query)
</script>

<template>
	<QueryBuilderEmptyState v-if="!props.query.dataSource" />
	<div
		v-show="props.query.dataSource"
		class="relative flex h-full w-full divide-x overflow-hidden"
	>
		<teleport to="#model-sidebar">
			<QueryOperations />
		</teleport>
		<div class="flex h-full w-full flex-col overflow-hidden pt-0 pr-0">
			<QueryBuilderToolbar></QueryBuilderToolbar>
			<QueryBuilderTable></QueryBuilderTable>
		</div>
	</div>
</template>
