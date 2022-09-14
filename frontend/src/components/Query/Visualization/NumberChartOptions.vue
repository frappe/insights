<script setup>
import { inject } from 'vue'
import Autocomplete from '@/components/Controls/Autocomplete.vue'

const query = inject('query')
const visualization = inject('visualization')
</script>

<template>
	<div class="space-y-2 text-gray-600">
		<div class="text-base font-light text-gray-500">Select Column</div>
		<Autocomplete
			v-model="visualization.data.valueColumn"
			:options="query.columns.valueOptions"
		/>
	</div>
</template>
