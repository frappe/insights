<script setup>
import UsePopover from '@/components/UsePopover.vue'
import { inject, ref } from 'vue'
import ChartOptions from './ChartOptions.vue'
const targetElement = ref(null)
const chart = inject('chart')
</script>

<template>
	<div ref="targetElement" class="flex h-full w-full items-center px-2">
		<div class="flex items-center space-x-1.5">
			<FeatherIcon name="settings" class="h-3.5 w-3.5 text-gray-500"></FeatherIcon>
			<span class="text-sm">Options</span>
		</div>
	</div>
	<UsePopover v-if="targetElement" :targetElement="targetElement" placement="bottom-end">
		<template #default="{ toggle }">
			<div class="h-[22rem] w-[15rem] overflow-y-auto rounded bg-white text-base shadow">
				<ChartOptions :onClose="() => toggle(false)" />
			</div>
		</template>
	</UsePopover>
</template>
