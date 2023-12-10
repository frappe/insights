<script setup>
import Checkbox from '@/components/Controls/Checkbox.vue'
import Color from '@/components/Controls/Color.vue'
import ListPicker from '@/components/Controls/ListPicker.vue'
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

if (!Array.isArray(options.value.yAxis)) {
	options.value.yAxis = typeof options.value.yAxis === 'string' ? [options.value.yAxis] : []
}

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
			<span class="mb-2 block text-sm leading-4 text-gray-700">X Axis</span>
			<Autocomplete v-model="options.xAxis" :returnValue="true" :options="indexOptions" />
		</div>
		<div>
			<span class="mb-2 block text-sm leading-4 text-gray-700">Y Axis</span>
			<ListPicker
				:value="options.yAxis"
				:options="valueOptions"
				@update:modelValue="options.yAxis = $event.map((item) => item.value)"
			/>
		</div>

		<div>
			<span class="mb-2 block text-sm leading-4 text-gray-700">Reference Line</span>
			<Autocomplete
				:modelValue="options.referenceLine"
				:options="['Average', 'Median', 'Min', 'Max']"
				@update:modelValue="options.referenceLine = $event.value"
			/>
		</div>

		<Color label="Colors" v-model="options.colors" :max="options.yAxis?.length || 1" multiple />

		<Input
			type="select"
			label="Rotate Labels"
			v-model="options.rotateLabels"
			:options="['0', '45', '90']"
		/>

		<Checkbox v-model="options.stack" label="Stack Values" />

		<Checkbox v-model="options.invertAxis" label="Switch X and Y Axis" />
	</div>
</template>
