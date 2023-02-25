<template>
	<div class="flex flex-1 flex-col overflow-scroll scrollbar-hide">
		<div class="flex flex-1 flex-shrink-0 flex-col lg:flex-row">
			<TablePanel />
			<ColumnPanel />
			<FilterPanel />
		</div>
		<QueryResult />
	</div>
</template>

<script setup>
import TablePanel from '@/query/Table/TablePanel.vue'
import ColumnPanel from '@/query/Column/ColumnPanel.vue'
import FilterPanel from '@/query/Filter/FilterPanel.vue'
import QueryResult from '@/query/Result/QueryResult.vue'
</script>
