<script setup>
import { inject } from 'vue'
import Checkbox from '@/components/Controls/Checkbox.vue'
import Autocomplete from '@/components/Controls/Autocomplete.vue'
import ListPicker from '@/components/Controls/ListPicker.vue'

const query = inject('query')
const chart = inject('chart')
</script>

<template>
	<div class="space-y-2 text-gray-600">
		<div class="text-gray-500">Select Dimension</div>
		<Autocomplete v-model="chart.data.labelColumn" :options="query.columns.indexOptions" />
	</div>

	<div class="space-y-2 text-gray-600">
		<div class="text-gray-500">Select Measure</div>
		<ListPicker
			:value="chart.data.valueColumn"
			:options="query.columns.valueOptions"
			@change="(options) => (chart.data.valueColumn = options)"
		/>
	</div>

	<div class="space-y-2 text-gray-600">
		<Checkbox v-model="chart.options.smoothLines" label="Enable Curved Lines" />
	</div>

	<div class="space-y-2 text-gray-600">
		<Checkbox v-model="chart.options.showPoints" label="Show Data Points" />
	</div>
</template>
