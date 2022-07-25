<template>
	<div class="flex items-baseline space-x-1 whitespace-nowrap">
		<ExpressionTerm :term="props.expression.left" />
		<div class="text-sm font-medium text-green-600">{{ props.expression.operator }}</div>
		<ExpressionTerm :term="props.expression.right" />
	</div>
</template>

<script setup>
import ExpressionTerm from '@/components/Query/Filter/ExpressionTerm.vue'

const props = defineProps({
	expression: {
		type: Object,
		required: true,
	},
})
</script>
