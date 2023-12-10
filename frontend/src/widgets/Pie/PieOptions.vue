<script setup>
import Checkbox from '@/components/Controls/Checkbox.vue'
import Color from '@/components/Controls/Color.vue'
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
			<span class="mb-2 block text-sm leading-4 text-gray-700">Label Column</span>
			<Autocomplete v-model="options.xAxis" :returnValue="true" :options="indexOptions" />
		</div>
		<div>
			<span class="mb-2 block text-sm leading-4 text-gray-700">Value Column</span>
			<Autocomplete v-model="options.yAxis" :returnValue="true" :options="valueOptions" />
		</div>

		<div>
			<span class="mb-2 block text-sm leading-4 text-gray-700">Maximum Slices</span>
			<Input v-model="options.maxSlices" type="number" min="1" />
		</div>

		<Color
			label="Colors"
			v-model="options.colors"
			:max="parseInt(options.maxSlices) + 1"
			multiple
		/>

		<div v-show="!options.inlineLabels">
			<span class="mb-2 block text-sm leading-4 text-gray-700">Label Position</span>
			<Autocomplete
				v-model="options.labelPosition"
				:options="['Top', 'Left', 'Bottom', 'Right']"
			/>
		</div>

		<Checkbox v-model="options.inlineLabels" label="Inline Labels" />
		<Checkbox v-model="options.scrollLabels" label="Paginate Labels" />
	</div>
</template>
