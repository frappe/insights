<template>
	<div
		class="group relative flex h-9 w-fit cursor-pointer items-center rounded-md border px-2 hover:bg-gray-50"
		@click.prevent.stop="$emit('edit')"
	>
		<BinaryExpression
			v-if="props.expression.type == 'BinaryExpression'"
			:expression="props.expression"
		/>
		<CallExpression
			v-else-if="props.expression.type == 'CallExpression'"
			:expression="props.expression"
		/>
		<FeatherIcon
			name="x"
			class="ml-2 h-3 w-3 self-center text-gray-500 hover:text-gray-700"
			@click.prevent.stop="$emit('remove')"
		/>
	</div>
</template>

<script setup>
import BinaryExpression from '@/components/Query/Filter/BinaryExpression.vue'
import CallExpression from '@/components/Query/Filter/CallExpression.vue'

defineEmits(['edit', 'remove'])
const props = defineProps({
	expression: {
		type: Object,
		required: true,
		validate: (value) => value.type === 'BinaryExpression' || value.type === 'CallExpression',
	},
})
</script>
