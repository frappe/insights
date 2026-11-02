<script setup lang="ts">
// What a page says in place of content it could not load: Not Found, No Access, or a failure
defineProps<{ title: string; detail?: string }>()
</script>

<template>
	<div class="flex w-full flex-1 flex-col items-center justify-center gap-1 p-4 text-center">
		<p class="text-base-medium text-ink-gray-8">{{ title }}</p>
		<p v-if="detail" class="text-p-sm text-ink-gray-5">{{ detail }}</p>
		<slot />
	</div>
</template>
