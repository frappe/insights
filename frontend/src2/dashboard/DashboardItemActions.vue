<script setup lang="ts">
import { Button } from 'frappe-ui'
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
<!-- Each action is a button, and not a div that listens: the grid lets a press
	through when it lands on a native control, so a control drawn as anything else
	starts a drag under the reader's finger. -->
<template>
	<div class="flex w-fit rounded-4 bg-surface-gray-9 shadow-sm">
		<Button
			v-for="action in actions"
			:key="action.label"
			variant="ghost"
			:label="action.label"
			class="!text-ink-gray-1 hover:!bg-surface-gray-8"
			@click="action.onClick()"
		>
			<template #icon>
				<component :is="action.icon" class="h-3.5 w-3.5" />
			</template>
		</Button>
	</div>
</template>
