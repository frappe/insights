<script setup lang="ts">
import type { Part } from './upgrade_steps'

// A sentence whose names stand out: people, titles, doctypes and teams.
defineProps<{ parts: Part[]; muted?: boolean }>()
</script>

<template>
	<template v-for="(part, index) in parts" :key="index">
		<span
			v-if="part.em"
			class="font-semibold"
			:class="muted ? 'text-ink-gray-6' : 'text-ink-gray-9'"
			>{{ part.text }}</span
		>
		<template v-else>{{ part.text }}</template>
	</template>
</template>
