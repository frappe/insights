<template>
	<div class="inline-flex w-full flex-wrap">
		<div class="font-code whitespace-nowrap font-medium text-purple-700">
			{{ props.expression.function }}
		</div>
		<div class="font-code text-purple-700">(</div>
		<div v-for="(arg, idx) in props.expression.arguments" class="flex items-center">
			<ExpressionTerm :term="arg" />
			<div v-if="idx < props.expression.arguments.length - 1">,&nbsp;</div>
		</div>
		<div class="font-code text-purple-700">)</div>
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
