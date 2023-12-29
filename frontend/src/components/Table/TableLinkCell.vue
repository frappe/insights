<script setup>
import { LinkIcon } from 'lucide-vue-next'

const props = defineProps({
	label: { type: String, required: true },
	url: { type: String, required: true },
})
</script>

<template>
	<a :href="url" target="_blank" class="flex items-center gap-1 hover:underline">
		<LinkIcon class="h-3 w-3" />
		<span>{{ label }}</span>
	</a>
</template>
