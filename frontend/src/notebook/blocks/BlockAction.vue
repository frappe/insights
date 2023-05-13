<script setup>
const props = defineProps({
	label: String,
	icon: String,
	iconComponent: Object,
	action: Function,
})
</script>

<template>
	<div
		class="flex h-8 cursor-pointer items-center rounded-md border border-gray-200 bg-white px-2 hover:bg-gray-50 hover:text-gray-800"
		@click.prevent.stop="action"
	>
		<slot>
			<div class="flex items-center space-x-1.5">
				<component
					v-if="iconComponent"
					:is="iconComponent"
					class="h-4 w-4 text-gray-400"
				></component>
				<FeatherIcon v-else :name="icon" class="h-4 w-4 text-gray-400"></FeatherIcon>
				<span class="text-sm">{{ label }}</span>
			</div>
		</slot>
	</div>
</template>
