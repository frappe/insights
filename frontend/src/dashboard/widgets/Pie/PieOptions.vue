<script setup>
import Checkbox from '@/components/Controls/Checkbox.vue'
import Color from '@/components/Controls/Color.vue'
import { FIELDTYPES } from '@/utils'
import { computed, inject } from 'vue'
import QueryOption from '../QueryOption.vue'

const emit = defineEmits(['update:modelValue'])
const props = defineProps({
	modelValue: { type: Object, required: true },
})

const options = computed({
	get() {
		return props.modelValue
	},
	set(value) {
		emit('update:modelValue', value)
	},
})

const dashboard = inject('dashboard')
const queryResource = computed(() => {
	if (!options.value.query) return []
	return dashboard.queries[options.value.query]
})
const indexOptions = computed(() => {
	return queryResource.value?.resultColumns
		?.filter((column) => !FIELDTYPES.NUMBER.includes(column.type))
		.map((column) => ({
			label: column.column,
			value: column.column,
			description: column.type,
		}))
})
const valueOptions = computed(() => {
	return queryResource.value?.resultColumns
		?.filter((column) => FIELDTYPES.NUMBER.includes(column.type))
		.map((column) => ({
			label: column.column,
			value: column.column,
			description: column.type,
		}))
})
</script>

<template>
	<div class="space-y-4">
		<QueryOption v-model="options.query" />
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
			<Autocomplete v-model.value="options.yAxis" :options="valueOptions" />
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
				v-model.value="options.labelPosition"
				:options="['Top', 'Left', 'Bottom', 'Right']"
			/>
		</div>

		<Checkbox v-model="options.inlineLabels" label="Inline Labels" />
		<Checkbox v-model="options.scrollLabels" label="Paginate Labels" />
	</div>
</template>
