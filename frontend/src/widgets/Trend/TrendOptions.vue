<script setup>
import { FIELDTYPES } from '@/utils'
import { Check } from 'lucide-vue-next'
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
			<label class="mb-1.5 block text-xs text-gray-600">Date Column</label>
			<Autocomplete v-model="options.dateColumn" :returnValue="true" :options="dateOptions" />
		</div>
		<div>
			<label class="mb-1.5 block text-xs text-gray-600">Value Column</label>
			<Autocomplete
				v-model="options.valueColumn"
				:returnValue="true"
				:options="valueOptions"
			/>
		</div>
		<FormControl
			label="Prefix"
			type="text"
			v-model="options.prefix"
			placeholder="Enter a prefix..."
		/>
		<FormControl
			label="Suffix"
			type="text"
			v-model="options.suffix"
			placeholder="Enter a suffix..."
		/>
		<Checkbox v-model="options.showTrendLine" label="Show Trend Line" />
		<Checkbox v-model="options.shorten" label="Shorten Numbers" />
		<Checkbox v-model="options.reverseDelta" label="Reverse Colors" />
	</div>
</template>
