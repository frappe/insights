<script setup>
import { inject, computed } from 'vue'
import ListPicker from '@/components/Controls/ListPicker.vue'

const query = inject('query')
const visualization = inject('visualization')

const allColumns = computed(() => {
	return query.doc.columns.map((c) => {
		return {
			label: c.label,
			value: c.column || c.label,
		}
	})
})
</script>

<template>
	<div class="space-y-2 text-gray-600">
		<div class="text-base font-light text-gray-500">Select Columns</div>
		<ListPicker
			:options="allColumns"
			:value="visualization.data.columns"
			@change="(options) => (visualization.data.columns = options)"
		/>
	</div>
</template>
