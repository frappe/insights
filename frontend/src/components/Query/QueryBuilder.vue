<template>
	<div class="relative flex min-h-[50%] flex-1">
		<TablePanel />
		<ColumnPanel />
		<FilterPanel />
	</div>
	<QueryResult />
</template>

<script setup>
import TablePanel from '@/components/Query/Table/TablePanel.vue'
import ColumnPanel from '@/components/Query/Column/ColumnPanel.vue'
import FilterPanel from '@/components/Query/Filter/FilterPanel.vue'
import QueryResult from '@/components/Query/Result/QueryResult.vue'
</script>
