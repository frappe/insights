<template>
	<div
		class="group relative flex h-9 w-fit cursor-pointer items-center rounded-md border px-2 hover:bg-gray-50"
		@click.prevent.stop="$emit('edit')"
	>
		<BinaryExpression v-if="expression.type == 'BinaryExpression'" :expression="expression" />
		<CallExpression v-else-if="expression.type == 'CallExpression'" :expression="expression" />
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
import { inject, reactive, unref } from 'vue'

defineEmits(['edit', 'remove'])
const props = defineProps({
	expression: {
		type: Object,
		required: true,
		validate: (value) => value.type === 'BinaryExpression' || value.type === 'CallExpression',
	},
})

let expression = reactive(unref(props.expression))

const isStringOrNumber = (arg) => arg.type == 'String' || arg.type == 'Number'
const isSimpleFilter =
	(expression.type == 'BinaryExpression' &&
		expression.left.type == 'Column' &&
		isStringOrNumber(expression.right)) ||
	(expression.type == 'CallExpression' &&
		expression.arguments[0].type == 'Column' &&
		expression.arguments.slice(1).every(isStringOrNumber))

const query = inject('query')
if (isSimpleFilter) {
	const simpleFilter = query.filters.convertIntoSimpleFilter(expression)
	if (simpleFilter) {
		expression = reactive({
			type: 'BinaryExpression',
			left: {
				type: 'Column',
				value: {
					table: simpleFilter.column?.table_label,
					column: simpleFilter.column?.label,
				},
			},
			operator: simpleFilter.operator.label,
			right: {
				type: 'String',
				value: simpleFilter.value.label,
			},
		})
	}
}
</script>
