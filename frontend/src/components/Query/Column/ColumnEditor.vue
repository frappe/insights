<template>
	<div class="mb-4 flex h-7 items-center">
		<Button icon="chevron-left" class="mr-2" @click="$emit('close')"> </Button>
		<div class="text-sm uppercase tracking-wide text-gray-600">Edit Column</div>
	</div>
	<div class="flex flex-col space-y-3">
		<ColumnExpressionPicker
			v-if="props.column.is_expression"
			:column="props.column"
			@close="$emit('close')"
		/>
		<SimpleColumnPicker v-else :column="props.column" @close="$emit('close')" />
	</div>
</template>

<script setup>
import SimpleColumnPicker from '@/components/Query/Column/SimpleColumnPicker.vue'
import ColumnExpressionPicker from '@/components/Query/Column/ColumnExpressionPicker.vue'

const emit = defineEmits(['close'])
const props = defineProps({
	column: {
		type: Object,
		default: {},
		required: true,
	},
})
</script>
