<script setup>
import UsePopover from '@/components/UsePopover.vue'
import { inject, ref } from 'vue'
import ChartOptions from './ChartOptions.vue'
const targetElement = ref(null)
const chart = inject('chart')
</script>

<template>
	<div
		v-if="chart.doc.query"
		ref="targetElement"
		class="flex h-8 cursor-pointer items-center rounded-md border border-gray-200 bg-white px-2 hover:bg-gray-50 hover:text-gray-800"
	>
		<div class="flex items-center space-x-1.5">
			<FeatherIcon name="settings" class="h-3.5 w-3.5 text-gray-400"></FeatherIcon>
			<span class="text-sm">Chart Options</span>
		</div>
	</div>
	<UsePopover v-if="targetElement" :targetElement="targetElement" placement="left-start">
		<template #default="{ toggle }">
			<div
				class="h-[22rem] w-[15rem] overflow-y-scroll rounded-lg border bg-white text-base shadow-sm"
			>
				<ChartOptions :onClose="() => toggle(false)" />
			</div>
		</template>
	</UsePopover>
</template>
