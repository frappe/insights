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
		<Autocomplete v-model="chart.data.labelColumn" :options="query.columns.indexOptions" />
	</div>

	<div class="space-y-2 text-gray-600">
		<div class="text-base font-light text-gray-500">Select Measure</div>
		<ListPicker
			:value="chart.data.valueColumn"
			:options="query.columns.valueOptions"
			@change="(options) => (chart.data.valueColumn = options)"
		/>
	</div>

	<Color
		label="Colors"
		v-model="chart.options.colors"
		:max="chart.data?.valueColumn?.length || 1"
		multiple
	/>
</template>
