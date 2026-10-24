<script setup lang="ts">
import { computed } from 'vue'
import useUserStore from '../users/users'
import { access, type Shared } from './access'

const props = defineProps<{ item: Shared }>()

const userStore = useUserStore()
const shown = computed(() => access(props.item, userStore.getName))
const roles = computed(() => props.item.visible_to_roles || [])
</script>

<template>
	<Tooltip :text="roles.join(', ')" :disabled="!roles.length">
		<div
			class="relative flex min-w-0 items-center rounded-4 focus:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
			:tabindex="roles.length ? 0 : undefined"
		>
			<component :is="shown.icon" class="size-4 shrink-0 text-ink-gray-5" />
			<span class="ml-2 truncate text-base text-ink-gray-6">{{ shown.label }}</span>
		</div>
	</Tooltip>
</template>
