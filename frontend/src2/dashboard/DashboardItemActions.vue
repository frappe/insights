<script setup lang="ts">
import { Pencil, Trash2 } from 'lucide-vue-next'
import { inject } from 'vue'
import { Dashboard } from './dashboard'
import { __ } from '../translation'

const emit = defineEmits({ edit: () => true })
const props = defineProps<{ itemIndex: number }>()

const dashboard = inject('dashboard') as Dashboard

const actions = [
	{
		icon: Pencil,
		label: __('Edit'),
		onClick: () => (dashboard.editingItemIndex = props.itemIndex),
	},
	{
		icon: Trash2,
		label: __('Delete'),
		onClick: () => dashboard.removeItem(props.itemIndex),
	},
]
</script>
<template>
	<div class="flex w-fit cursor-pointer rounded bg-surface-gray-9 shadow-sm">
		<div
			v-for="action in actions"
			:key="action.label"
			class="rounded p-1.5 hover:bg-surface-gray-8"
			@click="action.onClick()"
		>
			<component :is="action.icon" class="h-3.5 w-3.5 text-ink-gray-1" />
		</div>
	</div>
</template>
