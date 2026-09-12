<script setup lang="ts">
import { Pencil, Trash2 } from 'lucide-vue-next'
import { computed, inject } from 'vue'
import { Dashboard } from './dashboard'
import { __ } from '../translation'

const props = defineProps<{ itemIndex: number }>()

const dashboard = inject('dashboard') as Dashboard

// A chart is not edited from here. It is a workbook object, so its own card
// carries the edit action and this bar owns the layout only. A text or a filter
// has no object behind it, so the pencil opens its editor.
const actions = computed(() => {
	const edit = {
		icon: Pencil,
		label: __('Edit'),
		onClick: () => (dashboard.editingItemIndex = props.itemIndex),
	}
	const remove = {
		icon: Trash2,
		label: __('Delete'),
		onClick: () => dashboard.removeItem(props.itemIndex),
	}
	const item = dashboard.doc.items[props.itemIndex]
	return item?.type === 'chart' ? [remove] : [edit, remove]
})
</script>
<template>
	<div class="flex w-fit cursor-pointer rounded-4 bg-surface-gray-9 shadow-sm">
		<div
			v-for="action in actions"
			:key="action.label"
			class="rounded-4 p-1.5 hover:bg-surface-gray-8"
			@click="action.onClick()"
		>
			<component :is="action.icon" class="h-3.5 w-3.5 text-ink-gray-1" />
		</div>
	</div>
</template>
