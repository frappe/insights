<template>
	<div
		class="flex h-full w-full flex-shrink-0 flex-col rounded-md bg-white text-base text-gray-700"
	>
		<div class="-mx-3 flex h-[calc(100%-1.5rem)]">
			<TablePanel />
			<ColumnPanel />
			<FilterPanel />
		</div>
		<div class="flex h-6 flex-shrink-0">
			<LimitsAndOrder />
		</div>
	</div>
</template>

<script setup>
import TablePanel from '@/components/Query/Table/TablePanel.vue'
import ColumnPanel from '@/components/Query/Column/ColumnPanel.vue'
import FilterPanel from '@/components/Query/Filter/FilterPanel.vue'
import LimitsAndOrder from '@/components/Query/LimitsAndOrder.vue'
</script>
