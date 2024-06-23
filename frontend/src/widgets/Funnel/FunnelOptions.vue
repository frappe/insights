<script setup>
import ColorPalette from '@/components/Controls/ColorPalette.vue'
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

const indexOptions = computed(() => {
	return props.columns
		?.filter((column) => !FIELDTYPES.NUMBER.includes(column.type))
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
			<label class="mb-1.5 block text-xs text-gray-600">X Axis</label>
			<Autocomplete
				:options="indexOptions"
				:modelValue="options.xAxis"
				@update:modelValue="options.xAxis = $event?.value"
			/>
		</div>
		<div>
			<label class="mb-1.5 block text-xs text-gray-600">Y Axis</label>
			<Autocomplete
				:options="valueOptions"
				:modelValue="options.yAxis"
				@update:modelValue="options.yAxis = $event?.value"
			/>
		</div>

		<ColorPalette v-model="options.colors" />
	</div>
</template>
