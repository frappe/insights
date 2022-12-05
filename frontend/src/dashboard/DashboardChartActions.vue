<template>
	<div class="flex space-x-1">
		<div class="cursor-pointer rounded p-1 text-gray-600 hover:bg-gray-100">
			<FeatherIcon
				name="external-link"
				class="h-4 w-4"
				@mousedown.prevent.stop=""
				@click="$emit('edit')"
			/>
		</div>
		<div class="cursor-pointer rounded p-1 text-gray-600 hover:bg-gray-100">
			<FeatherIcon
				name="x"
				class="h-4 w-4"
				@mousedown.prevent.stop=""
				@click="$emit('remove')"
			/>
		</div>
	</div>
</template>

<script setup>
defineEmits(['edit', 'remove'])
</script>
