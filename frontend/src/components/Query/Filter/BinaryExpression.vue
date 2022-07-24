<template>
	<div class="flex space-x-1 whitespace-nowrap">
		<ExpressionTerm :term="expression.left" />
		<div>{{ expression.operator }}</div>
		<ExpressionTerm :term="expression.right" />
	</div>
</template>

<script setup>
import ExpressionTerm from '@/components/Query/Filter/ExpressionTerm.vue'
import { inject, reactive } from 'vue'

const query = inject('query')
const props = defineProps({
	expression: {
		type: Object,
		required: true,
	},
})

const expression = reactive({
	left: props.expression.left,
	operator: props.expression.operator,
	right: props.expression.right,
})

// const isSimpleBinaryExpression =
// 	props.expression.left.type == 'Column' &&
// 	(props.expression.right.type == 'String' || props.expression.right.type == 'Number')

// if (isSimpleBinaryExpression) {
// 	const simpleFilter = query.filters.convertIntoSimpleFilter(props.expression)
// 	if (simpleFilter) {
// 		expression.left.value.table = simpleFilter.column?.table_label
// 		expression.left.value.column = simpleFilter.column?.label
// 		expression.operator = simpleFilter.operator.label
// 		expression.right.value = simpleFilter.value.value
// 	}
// }
</script>
