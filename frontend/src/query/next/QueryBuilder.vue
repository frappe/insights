<script setup lang="ts">
import { provide } from 'vue'
import QueryBuilderSidebar from './QueryBuilderSidebar.vue'
import QueryBuilderTable from './QueryBuilderTable.vue'
import QueryBuilderToolbar from './QueryBuilderToolbar.vue'
import useQueryPipeline from './useQueryPipeline'

const queryPipeline = useQueryPipeline()
queryPipeline.setSource({ table: 'orderitems', data_source: 'Demo Data' })
provide('queryPipeline', queryPipeline)
</script>

<template>
	<div class="relative flex h-full w-full divide-x overflow-hidden">
		<div class="relative flex w-[20rem] flex-shrink-0 flex-col overflow-y-auto bg-white">
			<QueryBuilderSidebar></QueryBuilderSidebar>
		</div>
		<div class="flex h-full w-full flex-col overflow-hidden pt-0 pr-0">
			<QueryBuilderToolbar></QueryBuilderToolbar>
			<QueryBuilderTable></QueryBuilderTable>
		</div>
	</div>
</template>
