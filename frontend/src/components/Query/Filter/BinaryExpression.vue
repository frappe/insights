<template>
	<div class="inline-flex w-full flex-wrap items-baseline">
		<ExpressionTerm :term="props.expression.left" />
		<span class="w-1"></span>
		<p class="font-code whitespace-nowrap text-sm font-medium text-green-600">
			{{ props.expression.operator }}
		</p>
		<span class="w-1"></span>
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
