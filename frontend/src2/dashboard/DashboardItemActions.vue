<script setup lang="ts">
const emit = defineEmits({
	delete: () => true,
})
const actions = [
	{
		icon: 'trash',
		label: 'Delete',
		onClick: () => emit('delete'),
	},
]
</script>
<template>
	<div class="flex cursor-pointer rounded bg-gray-800 p-1 shadow-sm">
		<div
			v-for="action in actions"
			:key="action.label"
			class="px-1 py-0.5"
			@click="action.onClick()"
		>
			<FeatherIcon :name="action.icon" class="h-3.5 w-3.5 text-white" />
		</div>
	</div>
</template>
