<script setup>
import { defineAsyncComponent, computed, inject } from 'vue'
const props = defineProps(['chartType'])

const chart = inject('chart')

const component = computed(() => {
	switch (props.chartType) {
		case 'Bar':
			return defineAsyncComponent(() => import('./BarChartOptions.vue'))
		case 'Line':
			return defineAsyncComponent(() => import('./LineChartOptions.vue'))
		case 'Pie':
			return defineAsyncComponent(() => import('./PieChartOptions.vue'))
		case 'Table':
			return defineAsyncComponent(() => import('./TableChartOptions.vue'))
		case 'Number':
			return defineAsyncComponent(() => import('./NumberChartOptions.vue'))
		case 'Progress':
			return defineAsyncComponent(() => import('./ProgressChartOptions.vue'))
		default:
			return null
	}
})
</script>

<template>
	<div class="!mt-0 space-y-2 text-gray-600">
		<div class="text-base font-light text-gray-500">Title</div>
		<Input type="text" placeholder="Enter a suitable title..." v-model="chart.title" />
	</div>

	<component :is="component"></component>
</template>
