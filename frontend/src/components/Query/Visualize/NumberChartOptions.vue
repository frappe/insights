<script setup>
import { inject } from 'vue'
import Autocomplete from '@/components/Controls/Autocomplete.vue'

const query = inject('query')
const chart = inject('chart')
</script>

<template>
	<div class="space-y-2 text-gray-600">
		<div class="text-base font-light text-gray-500">Select Column</div>
		<Autocomplete v-model="chart.data.valueColumn" :options="query.columns.valueOptions" />
	</div>
	<div class="space-y-3 text-sm text-gray-600">
		<div class="space-y-1">
			<div class="font-light">Prefix</div>
			<Input type="text" v-model="chart.data.prefix" placeholder="Enter a prefix..." />
		</div>
		<div class="space-y-1">
			<div class="font-light">Suffix</div>
			<Input type="text" v-model="chart.data.suffix" placeholder="Enter a suffix..." />
		</div>
	</div>
</template>
