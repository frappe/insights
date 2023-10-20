<script setup>
import useDataSourceTable from '@/datasource/useDataSourceTable'

const props = defineProps({
	tablename: { type: String, required: true },
})
const table = await useDataSourceTable({ name: props.tablename })
</script>

<template>
	<div class="w-56 overflow-hidden rounded bg-white shadow">
		<div class="border-b bg-gray-50 px-4 py-2">
			<span class="truncate font-medium">{{ table.doc.label }}</span>
		</div>
		<div class="nowheel flex max-h-72 flex-col overflow-y-scroll">
			<div
				v-for="column in table.columns"
				:key="column.column"
				class="nodrag flex cursor-pointer items-center space-x-2 border-b px-4 py-2 hover:bg-gray-50"
			>
				<span class="text-gray-500"> # </span>
				<span class="truncate">{{ column.label }}</span>
				<!-- <Handle :id="column" type="source" :position="Position.Right" /> -->
			</div>
		</div>
	</div>
</template>
