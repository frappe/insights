<script setup>
import { FIELDTYPES } from '@/utils'
import { computed } from 'vue'

const emit = defineEmits(['update:modelValue'])
const props = defineProps({
	modelValue: { type: Object, required: true },
	columns: { type: Array, required: true },
})

const options = computed({
	get: () => props.modelValue,
	set: (value) => emit('update:modelValue', value),
})

const dateOptions = computed(() => {
	return props.columns
		?.filter((column) => FIELDTYPES.DATE.includes(column.type))
		.map((column) => ({
			label: column.label,
			value: column.label,
			description: column.type,
		}))
})
const valueOptions = computed(() => {
	return props.columns
		?.filter((column) => FIELDTYPES.NUMBER.includes(column.type))
		.map((column) => ({
			label: column.label,
			value: column.label,
			description: column.type,
		}))
})
</script>

<template>
	<div class="space-y-4">
		<FormControl
			type="text"
			label="Title"
			class="w-full"
			v-model="options.title"
			placeholder="Title"
		/>
		<div>
			<span class="mb-2 block text-sm leading-4 text-gray-700">Date Column</span>
			<Autocomplete v-model="options.dateColumn" :returnValue="true" :options="dateOptions" />
		</div>
		<div>
			<span class="mb-2 block text-sm leading-4 text-gray-700">Value Column</span>
			<Autocomplete
				v-model="options.valueColumn"
				:returnValue="true"
				:options="valueOptions"
			/>
		</div>
		<div>
			<span class="mb-2 block text-sm leading-4 text-gray-700">Prefix</span>
			<Input type="text" v-model="options.prefix" placeholder="Enter a prefix..." />
		</div>
		<div>
			<span class="mb-2 block text-sm leading-4 text-gray-700">Suffix</span>
			<Input type="text" v-model="options.suffix" placeholder="Enter a suffix..." />
		</div>
		<Checkbox v-model="options.showTrendLine" label="Show Trend Line" />
		<Checkbox v-model="options.shorten" label="Shorten Numbers" />
	</div>
</template>
