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
	if (!query.results.columns) return []
	return query.results.columns
		.filter((c) => FIELDTYPES.NUMBER.includes(c.type))
		.map((c) => ({ label: c.label, value: c.label, description: c.type }))
})
const allOptions = computed(() => {
	if (!query.results.columns) return []
	return query.results.columns.map((c) => ({
		label: c.label,
		value: c.label,
		description: c.type,
	}))
})

const errors = computed(() => {
	return {
		column:
			options.value.column &&
			[options.value.index, options.value.value].includes(options.value.column)
				? 'Column cannot be same as Row or Value'
				: '',
		index:
			options.value.index &&
			[options.value.column, options.value.value].includes(options.value.index)
				? 'Row cannot be same as Column or Value'
				: '',
		value:
			options.value.value &&
			[options.value.column, options.value.index].includes(options.value.value)
				? 'Value cannot be same as Column or Row'
				: '',
	}
})
</script>

<template>
	<div class="space-y-1">
		<span class="text-sm font-medium text-gray-700">Column</span>
		<Autocomplete
			v-model="options.column"
			:return-value="true"
			placeholder="Column"
			:options="allOptions"
		/>
		<span v-if="errors.column" class="text-xs text-red-500"> {{ errors.column }} </span>
	</div>
	<div class="space-y-1">
		<span class="text-sm font-medium text-gray-700">Row</span>
		<Autocomplete
			v-model="options.index"
			:return-value="true"
			placeholder="Row"
			:options="allOptions"
		/>
		<span v-if="errors.index" class="text-xs text-red-500"> {{ errors.index }} </span>
	</div>
	<div class="space-y-1">
		<span class="text-sm font-medium text-gray-700">Value</span>
		<Autocomplete
			v-model="options.value"
			:return-value="true"
			placeholder="Value"
			:options="valueOptions"
		/>
		<span v-if="errors.value" class="text-xs text-red-500"> {{ errors.value }} </span>
	</div>
</template>
