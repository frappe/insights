<template>
	<div class="flex">
		<div class="flex-1">
			<p class="font-medium leading-6 text-gray-900">{{ label }}</p>
			<span class="text-gray-600">
				{{ description }}
			</span>
		</div>
		<div class="flex flex-1 items-center pl-20">
			<slot />
		</div>
	</div>
</template>

<script setup>
const props = defineProps({
	label: {
		type: String,
		required: true,
	},
	description: {
		type: String,
		required: true,
	},
})
</script>
