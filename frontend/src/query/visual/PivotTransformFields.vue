<script setup>
import { FIELDTYPES } from '@/utils'
import { computed, inject } from 'vue'

const props = defineProps({ transformOptions: Object })
const query = inject('query')

const valueOptions = computed(() => {
	if (!query.resultColumns) return []
	return query.resultColumns
		.filter((c) => FIELDTYPES.NUMBER.includes(c.type))
		.map((c) => ({ label: c.label, value: c.label }))
})
const nonValueOptions = computed(() => {
	if (!query.resultColumns) return []
	return query.resultColumns
		.filter((c) => !FIELDTYPES.NUMBER.includes(c.type))
		.map((c) => ({ label: c.label, value: c.label }))
})
</script>

<template>
	<div class="space-y-1">
		<span class="text-sm font-medium text-gray-700">Column</span>
		<Autocomplete
			v-model="props.transformOptions.column"
			:return-value="true"
			placeholder="Column"
			:options="nonValueOptions.filter((c) => c.value != props.transformOptions.index)"
		/>
	</div>
	<div class="space-y-1">
		<span class="text-sm font-medium text-gray-700">Row</span>
		<Autocomplete
			v-model="props.transformOptions.index"
			:return-value="true"
			placeholder="Row"
			:options="nonValueOptions.filter((c) => c.value != props.transformOptions.column)"
		/>
	</div>
	<div class="space-y-1">
		<span class="text-sm font-medium text-gray-700">Value</span>
		<Autocomplete
			v-model="props.transformOptions.value"
			:return-value="true"
			placeholder="Value"
			:options="valueOptions"
		/>
	</div>
</template>
