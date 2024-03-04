<script setup lang="ts">
import { provide } from 'vue'
import VisualQueryBuilderSidebar from './VisualQueryBuilderSidebar.vue'
import VisualQueryBuilderTable from './VisualQueryBuilderTable.vue'
import useQueryPipeline from './useQueryPipeline'

const queryPipeline = useQueryPipeline()
provide('queryPipeline', queryPipeline)
</script>

<template>
	<div class="relative flex h-full w-full divide-x overflow-hidden">
		<div class="relative flex w-[22rem] flex-shrink-0 flex-col overflow-y-auto bg-white px-0.5">
			<VisualQueryBuilderSidebar></VisualQueryBuilderSidebar>
		</div>
		<div class="flex h-full w-full flex-col overflow-hidden p-4 pt-0 pl-0">
			<VisualQueryBuilderTable></VisualQueryBuilderTable>
		</div>
	</div>
</template>
