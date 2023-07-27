<script setup>
const props = defineProps({
	icon: { type: String, default: 'alert-triangle' },
	iconClass: { type: String, default: 'text-yellow-400' },
	title: { type: String, required: true, default: 'Invalid Widget' },
	message: {
		type: String,
		default: 'Remove this widget and try adding a new one.',
	},
})
</script>

<template>
	<div class="flex h-full w-full flex-col items-center justify-center">
		<!-- Invalid Widget -->
		<FeatherIcon :name="icon" class="h-6 w-6" :class="iconClass" />
		<span class="mt-2 text-gray-600">{{ title }}</span>
		<span class="text-center font-light text-gray-500">{{ message }}</span>
	</div>
</template>
