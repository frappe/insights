<script setup lang="ts">
import WorkbookQueryList from './WorkbookQueryList.vue'
import WorkbookChartList from './WorkbookChartList.vue'
</script>

<template>
	<div
		class="relative flex h-full w-[17rem] flex-shrink-0 flex-col overflow-y-auto border-r bg-white shadow-sm"
	>
		<WorkbookQueryList />
		<WorkbookChartList />
	</div>
</template>
