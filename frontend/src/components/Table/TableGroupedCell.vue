<script setup>
import { FlexRender } from '@tanstack/vue-table'
import { ChevronDown, ChevronRight } from 'lucide-vue-next'

const props = defineProps({
	row: { type: Object, required: true },
	cell: { type: Object, required: true },
})
</script>

<template>
	<div class="flex gap-1">
		<ChevronDown
			v-if="row.getIsExpanded()"
			class="h-4 w-4 cursor-pointer text-gray-600 hover:text-gray-800"
			@click="row.getToggleExpandedHandler()?.($event)"
		/>
		<ChevronRight
			v-else
			class="h-4 w-4 cursor-pointer text-gray-600 hover:text-gray-800"
			@click="row.getToggleExpandedHandler()?.($event)"
		/>
		<FlexRender :render="cell.column.columnDef.cell" :props="cell.getContext()" />
	</div>
</template>
