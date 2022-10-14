<script setup>
import { inject } from 'vue'
import Autocomplete from '@/components/Controls/Autocomplete.vue'
import Color from '@/components/Controls/Color.vue'

const query = inject('query')
const chart = inject('chart')
</script>

<template>
	<div class="space-y-2 text-gray-600">
		<div class="text-base font-light text-gray-500">Select Dimension</div>
		<Autocomplete v-model="chart.data.labelColumn" :options="query.columns.indexOptions" />
	</div>

	<div class="space-y-2 text-gray-600">
		<div class="text-base font-light text-gray-500">Select Column</div>
		<Autocomplete v-model="chart.data.valueColumn" :options="query.columns.valueOptions" />
	</div>

	<div class="space-y-2 text-gray-600">
		<div class="text-base font-light text-gray-500">Maximum Slices</div>
		<Input class="h-8" v-model="chart.options.maxSlices" type="number" />
	</div>

	<div class="space-y-2 text-gray-600">
		<div class="text-base font-light text-gray-500">Label Position</div>
		<Autocomplete
			v-model="chart.options.labelPosition"
			:options="['Top', 'Left', 'Bottom', 'Right']"
		/>
	</div>

	<Color
		label="Colors"
		v-model="chart.options.colors"
		:max="parseInt(chart.options.maxSlices)"
		multiple
	/>

	<Checkbox class="text-gray-600" v-model="chart.options.scrollLabels" label="Paginate Labels" />
</template>
