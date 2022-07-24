<template>
	<div class="flex items-center whitespace-nowrap">
		<div>{{ props.expression.function }}</div>
		<div>(</div>
		<div v-for="(arg, idx) in props.expression.arguments" class="flex items-center">
			<ExpressionTerm :term="arg" />
			<div v-if="idx < props.expression.arguments.length - 1">,&nbsp;</div>
		</div>
		<div>)</div>
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
