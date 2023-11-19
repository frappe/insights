<template>
	<div class="flex w-full flex-shrink-0 items-center bg-white pb-2">
		<Button icon="chevron-left" class="mr-2" @click="$emit('close')"> </Button>
		<div class="text-sm uppercase tracking-wide text-gray-700">Edit Column</div>
	</div>
	<div class="flex flex-1 flex-col overflow-y-scroll">
		<ColumnExpressionPicker
			v-if="props.column.is_expression"
			:column="props.column"
			@close="$emit('close')"
		/>
		<SimpleColumnPicker v-else :column="props.column" @close="$emit('close')" />
	</div>
</template>

<script setup>
import SimpleColumnPicker from './SimpleColumnPicker.vue'
import ColumnExpressionPicker from './ColumnExpressionPicker.vue'

const emit = defineEmits(['close'])
const props = defineProps({
	column: {
		type: Object,
		default: {},
		required: true,
	},
})
</script>
