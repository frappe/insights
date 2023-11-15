<script setup>
import { FIELDTYPES } from '@/utils'
import { computed, inject } from 'vue'

const emit = defineEmits(['update:transformOptions'])
const props = defineProps({ transformOptions: Object })
const query = inject('query')

const options = computed({
	get: () => props.transformOptions,
	set: (value) => emit('update:transformOptions', value),
})

const valueOptions = computed(() => {
	if (!query.resultColumns) return []
	return query.resultColumns
		.filter(
			(c) =>
				FIELDTYPES.NUMBER.includes(c.type) &&
				![options.value.column, options.value.index].includes(c.label)
		)
		.map((c) => ({ label: c.label, value: c.label, description: c.type }))
})
const allOptions = computed(() => {
	if (!query.resultColumns) return []
	return query.resultColumns.map((c) => ({ label: c.label, value: c.label, description: c.type }))
})
</script>

<template>
	<div class="space-y-1">
		<span class="text-sm font-medium text-gray-700">Column</span>
		<Autocomplete
			v-model="options.column"
			:return-value="true"
			placeholder="Column"
			:options="allOptions.filter((c) => ![options.index, options.value].includes(c.value))"
		/>
	</div>
	<div class="space-y-1">
		<span class="text-sm font-medium text-gray-700">Row</span>
		<Autocomplete
			v-model="options.index"
			:return-value="true"
			placeholder="Row"
			:options="allOptions.filter((c) => ![options.column, options.value].includes(c.value))"
		/>
	</div>
	<div class="space-y-1">
		<span class="text-sm font-medium text-gray-700">Value</span>
		<Autocomplete
			v-model="options.value"
			:return-value="true"
			placeholder="Value"
			:options="valueOptions"
		/>
	</div>
</template>
