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
</script>

<template>
	<div class="space-y-1">
		<span class="text-sm font-medium text-gray-700">Number Column</span>
		<Autocomplete
			v-model="options.column"
			:return-value="true"
			placeholder="Number Column"
			:options="valueOptions"
		/>
	</div>
</template>
