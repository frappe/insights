<script setup>
import { inject, ref } from 'vue'
import Checkbox from '@/components/Controls/Checkbox.vue'
import Autocomplete from '@/components/Controls/Autocomplete.vue'
import ListPicker from '@/components/Controls/ListPicker.vue'
import Color from '@/components/Controls/Color.vue'

const query = inject('query')
const chart = inject('chart')
const refLineOptions = ref([
	{ label: 'Average', value: 'average' },
	{ label: 'Min', value: 'min' },
	{ label: 'Max', value: 'max' },
	{ label: 'Median', value: 'median' },
])
</script>

<template>
	<div class="space-y-2 text-gray-600">
		<div class="text-gray-500">Select X Axis</div>
		<Autocomplete v-model="chart.config.labelColumn" :options="query.results.indexOptions" />
	</div>

	<div class="space-y-2 text-gray-600">
		<div class="text-gray-500">Select Y Axis</div>
		<ListPicker
			:value="chart.config.valueColumn"
			:options="query.results.valueOptions"
			@change="(options) => (chart.config.valueColumn = options)"
		/>
	</div>

	<div class="space-y-2 text-gray-600">
		<div class="text-base font-light text-gray-500">Reference Line</div>
		<Autocomplete v-model="chart.options.referenceLine" :options="refLineOptions" />
	</div>

	<Color
		label="Colors"
		v-model="chart.options.colors"
		:max="chart.config?.valueColumn?.length || 1"
		multiple
	/>

	<div class="space-y-2 text-gray-600">
		<Checkbox v-model="chart.options.smoothLines" label="Enable Curved Lines" />
	</div>

	<div class="space-y-2 text-gray-600">
		<Checkbox v-model="chart.options.showPoints" label="Show Data Points" />
	</div>
</template>
