<script setup lang="ts">
import { inject } from 'vue'
import { Dashboard } from './dashboard'

const emit = defineEmits({ edit: () => true })
const props = defineProps<{ itemIndex: number }>()

const dashboard = inject('dashboard') as Dashboard

const actions = [
	{
		icon: 'edit',
		label: 'Edit',
		onClick: () => (dashboard.editingItemIndex = props.itemIndex),
	},
	{
		icon: 'trash',
		label: 'Delete',
		onClick: () => dashboard.removeItem(props.itemIndex),
	},
]
</script>
<template>
	<div class="flex w-fit cursor-pointer rounded bg-gray-800 shadow-sm">
		<div
			v-for="action in actions"
			:key="action.label"
			class="rounded p-1.5 hover:bg-gray-700"
			@click="action.onClick()"
		>
			<FeatherIcon :name="action.icon" class="h-3.5 w-3.5 text-white" />
		</div>
	</div>
</template>
