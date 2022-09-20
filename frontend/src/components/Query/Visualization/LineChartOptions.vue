<script setup>
import { inject } from 'vue'
import Autocomplete from '@/components/Controls/Autocomplete.vue'
import ListPicker from '@/components/Controls/ListPicker.vue'

const query = inject('query')
const visualization = inject('visualization')
</script>

<template>
	<div class="space-y-2 text-gray-600">
		<div class="text-base font-light text-gray-500">Select Dimension</div>
		<Autocomplete
			v-model="visualization.data.labelColumn"
			:options="query.columns.indexOptions"
		/>
	</div>

	<div class="space-y-2 text-gray-600">
		<div class="text-base font-light text-gray-500">Select Measure</div>
		<ListPicker
			:value="visualization.data.valueColumn"
			:options="query.columns.valueOptions"
			@change="(options) => (visualization.data.valueColumn = options)"
		/>
	</div>

	<div class="space-y-2 text-gray-600">
		<div class="text-base font-light text-gray-500">Line Smoothness</div>
		<div class="flex w-full items-center">
			<input
				type="range"
				min="0"
				max="1"
				step="0.1"
				v-model="visualization.data.lineSmoothness"
				class="flex-1 focus:outline-none"
			/>
			<span class="ml-2 text-sm">{{ visualization.data.lineSmoothness }}</span>
		</div>
	</div>
</template>
