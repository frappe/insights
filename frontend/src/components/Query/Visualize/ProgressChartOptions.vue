<script setup>
import { inject } from 'vue'
import Autocomplete from '@/components/Controls/Autocomplete.vue'

const query = inject('query')
const chart = inject('chart')
</script>

<template>
	<div class="space-y-2 text-gray-600">
		<div class="text-base font-light text-gray-500">Select Progress Column</div>
		<Autocomplete v-model="chart.config.progressColumn" :options="query.columns.valueOptions" />
	</div>
	<div class="space-y-2 text-gray-600">
		<div class="text-base font-light text-gray-500">Select Target Column</div>
		<Autocomplete v-model="chart.config.targetColumn" :options="query.columns.valueOptions" />
	</div>
	<div class="space-y-3 text-sm text-gray-600">
		<div class="space-y-1">
			<div class="font-light">Prefix</div>
			<Input type="text" v-model="chart.options.prefix" placeholder="Enter a prefix..." />
		</div>
		<div class="space-y-1">
			<div class="font-light">Suffix</div>
			<Input type="text" v-model="chart.options.suffix" placeholder="Enter a suffix..." />
		</div>
		<div class="space-y-1">
			<div class="font-light">Decimals</div>
			<Input type="number" v-model="chart.options.decimals" placeholder="Enter a number..." />
		</div>

		<div class="space-y-2 text-gray-600">
			<Checkbox v-model="chart.options.shorten" label="Shorten Numbers" />
		</div>
	</div>
</template>
