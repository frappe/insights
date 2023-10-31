<script setup>
import { ArrowDownUp, ArrowDownWideNarrow, ArrowUpWideNarrow } from 'lucide-vue-next'
import { inject } from 'vue'

const props = defineProps({ column: Object })
const builder = inject('builder')
function getOrder(columnLabel) {
	return builder.query.columns.find((c) => c.label == columnLabel)?.order
}
</script>
<template>
	<div class="space-x-1">
		<ArrowDownUp
			v-if="!getOrder(column.label)"
			class="h-4 w-4 cursor-pointer text-gray-500 hover:text-gray-700"
			@click="builder.setOrderBy(column.label, 'asc')"
		/>
		<ArrowUpWideNarrow
			v-else-if="getOrder(column.label) == 'asc'"
			class="h-4 w-4 cursor-pointer text-gray-500 hover:text-gray-700"
			@click="builder.setOrderBy(column.label, 'desc')"
		/>
		<ArrowDownWideNarrow
			v-else-if="getOrder(column.label) == 'desc'"
			class="h-4 w-4 cursor-pointer text-gray-500 hover:text-gray-700"
			@click="builder.setOrderBy(column.label, '')"
		/>
	</div>
</template>
