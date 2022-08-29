<template>
	<div class="h-screen min-h-[44rem] min-w-[80rem] bg-gray-50 font-sans">
		<CommandPalette />
		<AppShell />
		<Toasts />
	</div>
</template>

<script setup>
import Toasts from '@/utils/toasts'
import AppShell from '@/components/AppShell.vue'
import CommandPalette from '@/components/CommandPalette.vue'
</script>
