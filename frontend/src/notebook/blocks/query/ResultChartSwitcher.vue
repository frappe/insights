<script setup>
import { inject } from 'vue'
const state = inject('state')
</script>

<template>
	<div class="flex h-7 items-center rounded-md bg-gray-100 p-0.5">
		<span
			class="flex h-full w-7 flex-1 cursor-pointer items-center justify-center rounded-md text-gray-600 transition-all hover:text-gray-800"
			:class="{ 'border bg-white shadow': state.resultOrChart == 'Result' }"
			@click="state.resultOrChart = 'Result'"
		>
			<FeatherIcon name="table" class="h-3 w-3"></FeatherIcon>
		</span>
		<span
			class="flex h-full w-7 flex-1 cursor-pointer items-center justify-center rounded-md text-gray-600 transition-all hover:text-gray-800"
			:class="{ 'border bg-white shadow': state.resultOrChart == 'Visualize' }"
			@click="state.resultOrChart = 'Visualize'"
		>
			<FeatherIcon name="bar-chart" class="h-3 w-3"></FeatherIcon>
		</span>
	</div>
</template>
