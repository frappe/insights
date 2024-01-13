<template>
	<div class="mb-2 flex items-center justify-between">
		<div class="flex items-center space-x-1.5">
			<component :is="icon" class="h-4 w-4 text-gray-600" />
			<p class="font-medium">{{ title }}</p>
		</div>
		<slot></slot>
	</div>
</template>

<script setup>
defineProps(['title', 'icon'])
</script>
