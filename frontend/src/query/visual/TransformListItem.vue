<script setup>
import { isEmptyObj } from '@/utils'
import { CornerLeftDown, CornerRightUp, Crop, Sigma, X } from 'lucide-vue-next'

defineEmits(['edit', 'remove'])
defineProps(['transform', 'isActive'])

const transformTypeToIcon = {
	Pivot: CornerRightUp,
	Unpivot: CornerLeftDown,
	Transpose: Crop,
	CumulativeSum: Sigma,
}
const transformTypeToLabel = {
	Pivot: 'Convert Row to Column',
	Unpivot: 'Convert Column to Row',
	Transpose: 'Transpose',
	CumulativeSum: 'Cumulative Sum',
}

function isValidTransform(transform) {
	return transform?.type && !isEmptyObj(transform.options)
}
</script>

<template>
	<div
		class="group flex h-8 w-full cursor-pointer items-center justify-between rounded border border-gray-300 bg-white px-2 hover:shadow"
		:class="isActive ? 'border-gray-500 bg-white shadow-sm ring-1 ring-gray-400' : ''"
		@click.prevent.stop="$emit('edit')"
	>
		<div class="flex w-full items-center overflow-hidden">
			<div class="flex w-full space-x-2 truncate" v-if="isValidTransform(transform)">
				<component
					:is="transformTypeToIcon[transform.type]"
					class="h-4 w-4 text-gray-600"
				/>
				<span class="truncate">{{ transformTypeToLabel[transform.type] }}</span>
			</div>
			<div v-else class="text-gray-600">Select a transform</div>
		</div>
		<div class="flex items-center space-x-2">
			<X
				class="invisible h-4 w-4 text-gray-600 transition-all hover:text-gray-800 group-hover:visible"
				@click.prevent.stop="$emit('remove')"
			/>
		</div>
	</div>
</template>
