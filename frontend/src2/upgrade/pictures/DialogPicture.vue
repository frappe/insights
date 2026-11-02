<script setup lang="ts">
// A dialog as frappe-ui's Dialog draws its card and title, standing in a
// picture with the rows of the real dialog inside it.
defineProps<{ title: string }>()
</script>

<template>
	<div
		class="flex flex-col gap-4 rounded-7 bg-surface-elevation-1 px-5 pb-5 pt-4 text-start shadow-sm ring-1 ring-outline-gray-1"
	>
		<div class="text-xl font-semibold leading-6 text-ink-gray-8">{{ title }}</div>
		<div class="flex flex-col gap-2 text-base">
			<slot />
		</div>
	</div>
</template>
