<script setup>
import { inject } from 'vue'
import ChartOptions from './ChartOptions.vue'
const state = inject('state')
</script>

<template>
	<Popover v-if="state.resultOrChart == 'Visualize'" placement="bottom-start">
		<template #target="{ togglePopover }">
			<div
				class="flex cursor-pointer items-center rounded-md border px-2 py-1.5 text-gray-600 transition-all hover:bg-gray-50 hover:text-gray-800"
				@click="togglePopover"
			>
				<FeatherIcon name="settings" class="h-3.5 w-3.5"></FeatherIcon>
			</div>
		</template>
		<template #body="{ isOpen }">
			<transition name="fade">
				<div
					v-show="isOpen"
					class="mt-1 h-[22rem] w-[15rem] overflow-y-scroll rounded-lg border bg-white text-base shadow"
				>
					<ChartOptions />
				</div>
			</transition>
		</template>
	</Popover>
</template>
