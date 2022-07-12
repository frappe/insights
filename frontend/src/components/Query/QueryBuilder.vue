<template>
	<div
		class="flex h-full min-h-[16rem] w-full flex-shrink-0 flex-col rounded-md bg-white text-base text-gray-700"
	>
		<div class="-mx-3 flex h-[calc(100%-1.5rem)]">
			<TablePicker />
			<ColumnPanel />
			<FilterPicker />
		</div>
		<div class="flex h-6 flex-shrink-0">
			<LimitsAndOrder />
		</div>
	</div>
</template>

<script setup>
import TablePicker from '@/components/Query/TablePicker.vue'
import ColumnPanel from '@/components/Query/ColumnPanel.vue'
import FilterPicker from '@/components/Query/FilterPicker.vue'
import LimitsAndOrder from '@/components/Query/LimitsAndOrder.vue'
</script>
