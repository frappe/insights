<template>
	<div class="flex items-baseline space-x-1 whitespace-nowrap">
		<span v-if="condition.left.label" class="flex items-baseline">
			{{ condition.left.label }}
		</span>
		<div v-else class="flex">
			<span>(</span>
			<Expression :condition="condition.left" />
			<span>)</span>
		</div>

		<span class="flex items-baseline text-sm text-green-600">
			{{ condition.operator.label }}
		</span>

		<span v-if="condition.right.label" class="flex items-baseline">
			{{ condition.right.label }}
		</span>
		<div v-else class="flex">
			<span>(</span>
			<Expression :condition="condition.right" />
			<span>)</span>
		</div>
	</div>
</template>

<script setup>
defineProps({
	condition: {
		type: Object,
		required: true,
	},
})
</script>
