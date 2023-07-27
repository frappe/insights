<script setup>
import { LoadingIndicator } from 'frappe-ui'

const props = defineProps({
	label: String,
	icon: String,
	iconComponent: Object,
	action: Function,
	loading: Boolean,
})
</script>

<template>
	<div
		class="flex h-8 cursor-pointer items-center rounded border border-gray-200 bg-white px-2 hover:bg-gray-50 hover:text-gray-800"
		@click.prevent.stop="() => !loading && action && action()"
	>
		<slot>
			<div class="flex items-center space-x-1.5">
				<component
					v-if="iconComponent"
					:is="iconComponent"
					class="h-4 w-4 text-gray-500"
				></component>
				<LoadingIndicator v-if="loading" class="h-4 w-4 text-gray-500" />
				<FeatherIcon v-else :name="icon" class="h-4 w-4 text-gray-500"></FeatherIcon>
				<span class="text-sm">{{ label }}</span>
			</div>
		</slot>
	</div>
</template>
