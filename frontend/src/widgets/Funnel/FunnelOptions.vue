<script setup>
import { FIELDTYPES } from '@/utils'
import { computed } from 'vue'
import ColorPalette from '@/components/Controls/ColorPalette.vue'

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
			<Autocomplete v-model="options.xAxis" :returnValue="true" :options="indexOptions" />
		</div>
		<div>
			<label class="mb-1.5 block text-xs text-gray-600">Y Axis</label>
			<Autocomplete v-model="options.yAxis" :returnValue="true" :options="valueOptions" />
		</div>

		<ColorPalette v-model="options.colors" />
	</div>
</template>
