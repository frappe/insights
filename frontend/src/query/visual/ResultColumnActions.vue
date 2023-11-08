<script setup>
import { ArrowDown, ArrowDownUp, ArrowUp } from 'lucide-vue-next'
import { inject } from 'vue'

const props = defineProps({ column: Object })
const builder = inject('builder')
function getOrder(columnLabel) {
	return builder.query.columns.find((c) => c.label == columnLabel)?.order
}
const sortOptions = [
	{
		label: 'Sort Ascending',
		onClick: () => builder.setOrderBy(props.column.label, 'asc'),
	},
	{
		label: 'Sort Descending',
		onClick: () => builder.setOrderBy(props.column.label, 'desc'),
	},
	{
		label: 'Remove Sort',
		onClick: () => builder.setOrderBy(props.column.label, ''),
	},
]
const sortOrderToIcon = {
	asc: ArrowUp,
	desc: ArrowDown,
}
</script>
<template>
	<div class="space-x-1">
		<Dropdown :options="sortOptions">
			<component
				:is="sortOrderToIcon[getOrder(column.label)] || ArrowDownUp"
				class="h-4 w-4 cursor-pointer text-gray-500 hover:text-gray-700"
			/>
		</Dropdown>
	</div>
</template>
