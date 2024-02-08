<template>
	<div class="flex items-center justify-between">
		<div class="flex items-center space-x-1.5">
			<component :is="icon" class="h-4 w-4 text-gray-600" />
			<Tooltip
				v-if="info"
				:text="info"
				bodyClasses="!max-w-[8rem] !text-left ml-1"
				placement="right"
			>
				<div class="flex items-baseline">
					<p class="cursor-pointer font-medium">{{ title }}</p>
					<span class="ml-1.5 font-mono text-xs text-gray-600"> i </span>
				</div>
			</Tooltip>
			<p v-else class="font-medium">{{ title }}</p>
		</div>
		<slot></slot>
	</div>
</template>

<script setup>
import Tooltip from '@/components/Tooltip.vue'

defineProps(['title', 'info', 'icon'])
</script>
