<script setup lang="ts">
// The "+ Add …" control at the foot of a config list. Not a frappe-ui Button:
// it reads as the list's last line rather than as an action beside it, which is
// why the config panel draws its own. One of them, so it is one look.
defineProps<{ label: string }>()
</script>

<template>
	<button
		type="button"
		class="mt-1.5 rounded-4 text-left text-xs text-ink-gray-5 hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
	>
		+ {{ label }}
	</button>
</template>
