<template>
	<div class="flex h-8 w-full cursor-pointer items-center rounded-md bg-gray-100 p-1">
		<div
			v-for="tab in tabs"
			class="flex h-full flex-1 items-center justify-center px-4 text-sm transition-all"
			:class="{
				'rounded bg-white shadow': tab.active,
				'cursor-not-allowed': tab.disabled,
			}"
			@click="$emit('switch', tab)"
		>
			{{ tab.label }}
		</div>
	</div>
</template>

<script setup>
const props = defineProps({
	tabs: {
		type: Array,
		required: true,
	},
})
defineEmits(['switch'])
</script>
