<script setup>
import { inject } from 'vue'
import Autocomplete from '@/components/Controls/Autocomplete.vue'
import Color from '@/components/Controls/Color.vue'

const query = inject('query')
const chart = inject('chart')
</script>

<template>
	<div class="space-y-2 text-gray-600">
		<div class="text-base font-light text-gray-500">Select X Axis</div>
		<Autocomplete v-model="chart.config.labelColumn" :options="query.results.indexOptions" />
	</div>

	<div class="space-y-2 text-gray-600">
		<div class="text-base font-light text-gray-500">Select Y Axis</div>
		<Autocomplete v-model="chart.config.valueColumn" :options="query.results.valueOptions" />
	</div>

	<div class="space-y-2 text-gray-600">
		<div class="text-base font-light text-gray-500">Maximum Slices</div>
		<Input class="h-8" v-model="chart.options.maxSlices" type="number" />
	</div>

	<Color
		label="Colors"
		v-model="chart.options.colors"
		:max="parseInt(chart.options.maxSlices)"
		multiple
	/>

	<div class="space-y-2 text-gray-600" v-show="!chart.options.inlineLabels">
		<div class="text-base font-light text-gray-500">Label Position</div>
		<Autocomplete
			v-model="chart.options.labelPosition"
			:options="['Top', 'Left', 'Bottom', 'Right']"
		/>
	</div>

	<Checkbox class="text-gray-600" v-model="chart.options.inlineLabels" label="Inline Labels" />
	<Checkbox class="text-gray-600" v-model="chart.options.scrollLabels" label="Paginate Labels" />
</template>
