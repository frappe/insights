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
import TablePanel from '@/components/Query/Table/TablePanel.vue'
import ColumnPanel from '@/components/Query/Column/ColumnPanel.vue'
import FilterPanel from '@/components/Query/Filter/FilterPanel.vue'
import QueryResult from '@/components/Query/Result/QueryResult.vue'
</script>
