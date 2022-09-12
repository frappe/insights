<template>
	<div class="relative flex h-1/2">
		<TablePanel />
		<ColumnPanel />
		<FilterPanel />
	</div>
	<div class="h-1/2">
		<QueryResult />
	</div>
</template>

<script setup>
import TablePanel from '@/components/Query/Table/TablePanel.vue'
import ColumnPanel from '@/components/Query/Column/ColumnPanel.vue'
import FilterPanel from '@/components/Query/Filter/FilterPanel.vue'
import QueryResult from '@/components/Query/Result/QueryResult.vue'
</script>
