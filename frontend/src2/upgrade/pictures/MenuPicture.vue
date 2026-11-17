<script setup lang="ts">
import { ItemListRow } from 'frappe-ui'
// An open menu as frappe-ui draws one: the floating panel, with a row per item.
// A real Dropdown opens in a portal at its trigger, so a picture lays the same
// rows out in place.
defineProps<{ items?: { label: string; icon: any; selected?: boolean }[] }>()
</script>

<template>
	<div
		class="min-w-48 rounded-6 bg-surface-elevation-2 p-1.5 text-start shadow-2xl ring-1 ring-black ring-opacity-5"
	>
		<slot>
			<ItemListRow v-for="item in items" :key="item.label" :selected="item.selected">
				<template #prefix>
					<component
						:is="item.icon"
						class="size-4 shrink-0 text-ink-gray-6"
						stroke-width="1.5"
					/>
				</template>
				<template #label>
					<span class="truncate">{{ item.label }}</span>
				</template>
			</ItemListRow>
		</slot>
	</div>
</template>
