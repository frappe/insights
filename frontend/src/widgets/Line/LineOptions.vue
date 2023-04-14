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
		<Input
			type="text"
			label="Title"
			class="w-full"
			v-model="options.title"
			placeholder="Title"
		/>
		<div>
			<span class="mb-2 block text-sm leading-4 text-gray-700">X Axis</span>
			<Autocomplete v-model.value="options.xAxis" :options="indexOptions" />
		</div>
		<div>
			<span class="mb-2 block text-sm leading-4 text-gray-700">Y Axis</span>
			<ListPicker
				:value="options.yAxis"
				:options="valueOptions"
				@change="options.yAxis = $event.map((item) => item.value)"
			/>
		</div>

		<div>
			<span class="mb-2 block text-sm leading-4 text-gray-700">Reference Line</span>
			<Autocomplete
				v-model.value="options.referenceLine"
				:options="['Average', 'Median', 'Min', 'Max']"
			/>
		</div>

		<Color label="Colors" v-model="options.colors" :max="options.yAxis?.length || 1" multiple />

		<div class="space-y-2 text-gray-600">
			<Checkbox v-model="options.smoothLines" label="Enable Curved Lines" />
		</div>

		<div class="space-y-2 text-gray-600">
			<Checkbox v-model="options.showPoints" label="Show Data Points" />
		</div>

		<div class="space-y-2 text-gray-600">
			<Checkbox v-model="options.showArea" label="Show Area" />
		</div>
	</div>
</template>
