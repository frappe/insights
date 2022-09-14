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
			:value="
				Array.isArray(visualization.data.valueColumn)
					? visualization.data.valueColumn
					: visualization.data.valueColumn
					? [visualization.data.valueColumn]
					: undefined
			"
			:options="query.columns.valueColumns"
			@selectOption="(options) => (visualization.data.valueColumn = options)"
		/>
	</div>
</template>
