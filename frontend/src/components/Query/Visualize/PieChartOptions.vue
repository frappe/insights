<script setup>
import { inject } from 'vue'
import Autocomplete from '@/components/Controls/Autocomplete.vue'

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
</template>
