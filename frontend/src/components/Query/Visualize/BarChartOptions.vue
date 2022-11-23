<script setup>
import { inject } from 'vue'
import Autocomplete from '@/components/Controls/Autocomplete.vue'
import ListPicker from '@/components/Controls/ListPicker.vue'
import Color from '@/components/Controls/Color.vue'

const query = inject('query')
const chart = inject('chart')
</script>

<template>
	<div class="space-y-2 text-gray-600">
		<div class="text-base font-light text-gray-500">Select Dimension</div>
		<Autocomplete v-model="chart.config.labelColumn" :options="query.results.indexOptions" />
	</div>

	<div class="space-y-2 text-gray-600">
		<div class="text-base font-light text-gray-500">Select Measure</div>
		<ListPicker
			:value="chart.config.valueColumn"
			:options="query.results.valueOptions"
			@change="(options) => (chart.config.valueColumn = options)"
		/>
	</div>

	<Color
		label="Colors"
		v-model="chart.options.colors"
		:max="chart.config?.valueColumn?.length || 1"
		multiple
	/>

	<div class="space-y-2 text-gray-600">
		<Input
			type="select"
			label="Rotate Labels"
			v-model="chart.options.rotateLabels"
			:options="['0', '45', '90']"
		/>
	</div>

	<div class="space-y-2 text-gray-600">
		<Checkbox v-model="chart.options.invertAxis" label="Switch X and Y Axis" />
	</div>
</template>
