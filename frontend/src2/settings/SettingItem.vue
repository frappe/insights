<script setup lang="ts">
const props = defineProps<{
	label: string
	description: string
}>()
</script>

<template>
	<div class="flex items-start justify-between gap-8 max-sm:flex-col max-sm:gap-2">
		<div class="flex w-3/4 flex-col max-sm:w-full">
			<span class="text-p-base-medium">{{ label }}</span>
			<span class="text-p-sm text-ink-gray-5">
				{{ description }}
			</span>
		</div>
		<div class="flex h-full w-1/4 items-center justify-end max-sm:w-auto">
			<slot />
		</div>
	</div>
</template>
