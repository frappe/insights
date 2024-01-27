<script setup>
import { fieldtypesToIcon } from '@/utils'
import { X } from 'lucide-vue-next'

defineProps(['column', 'isActive'])
defineEmits(['edit-column', 'remove-column'])

function isValidColumn(column) {
	const isExpression = column.expression?.raw
	return column.label && column.type && (isExpression || (column.table && column.column))
}

const aggregationToAbbr = {
	min: 'MIN',
	max: 'MAX',
	sum: 'SUM',
	avg: 'AVG',
	count: 'CNT',
	distinct: 'UDST',
	distinct_count: 'DCNT',
	'group by': 'UNQ',
	'cumulative count': 'CCNT',
	'cumulative sum': 'CSUM',
}
function getAbbreviation(column) {
	if (column.expression?.raw) return 'EXPR'
	return aggregationToAbbr[column.aggregation] || 'UNQ'
}
</script>

<template>
	<div
		class="group relative flex h-8 flex-1 cursor-pointer items-center justify-between overflow-hidden rounded border border-gray-300 bg-white px-2 pl-2.5 hover:shadow"
		:class="isActive ? 'border-gray-500 bg-white shadow-sm ring-1 ring-gray-400' : ''"
		@click.prevent.stop="$emit('edit-column', column)"
	>
		<div class="absolute left-0 h-full w-1 flex-shrink-0 bg-blue-500"></div>
		<div class="flex w-full items-center overflow-hidden">
			<div class="flex w-full items-center space-x-1.5 truncate" v-if="isValidColumn(column)">
				<!-- <div
					class="rounded border border-violet-400 py-0.5 px-1 font-mono text-xs tracking-wider text-violet-700"
				>
					{{ getAbbreviation(column) }}
				</div> -->
				<component :is="fieldtypesToIcon[column.type]" class="h-4 w-4 text-gray-600" />
				<div>{{ column.label }}</div>
			</div>
			<div v-else class="text-gray-600">Select a column</div>
		</div>
		<div class="flex items-center space-x-2">
			<X
				class="invisible h-4 w-4 text-gray-600 transition-all hover:text-gray-800 group-hover:visible"
				@click.prevent.stop="$emit('remove-column', column)"
			/>
		</div>
	</div>
</template>
